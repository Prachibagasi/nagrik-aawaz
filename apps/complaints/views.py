import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.serializers import ValidationError as SerializerValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView

from apps.core.pagination import StandardResultsPagination
from apps.core.permissions import IsOfficer, IsAdmin, IsOwnerOrAdmin
from .filters import ComplaintFilter
from .models import Category, Complaint, IssueVerification
from .serializers import (
    CategorySerializer,
    ComplaintListSerializer,
    ComplaintDetailSerializer,
    ComplaintCreateSerializer,
    ComplaintStatusUpdateSerializer,
    ComplaintAssignSerializer,
    quantize_lat_lng,
)
from .services.complaint_service import (
    update_complaint_status,
    assign_complaint,
    upvote_complaint,
    get_complaint_stats,
)
from .services.demo_intel import find_similar_complaints, past_resolutions, sla_estimate
from .services.phase2.clustering import find_cluster_complaints
from .services.phase2.sla_prediction import predict_sla_full, sentiment_trend_series
from .services.phase2.auto_assignment import suggest_assignee

logger = logging.getLogger(__name__)
User = get_user_model()


# ─── Categories ───────────────────────────────────────────────────────────────

class CategoryListView(APIView):
    """GET /api/v1/complaints/categories/ — public"""

    permission_classes = [AllowAny]

    def get(self, request):
        qs = Category.objects.filter(is_active=True)
        return Response(CategorySerializer(qs, many=True).data)


# ─── Complaints ───────────────────────────────────────────────────────────────

class ComplaintListCreateView(APIView):
    """
    GET  /api/v1/complaints/       — list (public for anonymous; user sees own)
    POST /api/v1/complaints/       — submit new complaint
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        qs = Complaint.objects.select_related("category", "user", "assigned_to")

        if request.user.is_authenticated and request.user.role == "citizen":
            qs = qs.filter(user=request.user)
        elif not request.user.is_authenticated:
            qs = qs.filter(is_anonymous=False)

        filterset = ComplaintFilter(request.GET, queryset=qs)
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)

        qs = filterset.qs
        search = request.GET.get("search", "")
        if search:
            qs = qs.filter(description__icontains=search)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs.order_by("-created_at"), request)
        serializer = ComplaintListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ComplaintCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        complaint = serializer.save()

        # Async: trigger AI classification (handled via signal or task in later module)
        logger.info("New complaint created: %s", complaint.tracking_id)

        return Response(
            {
                "message": "Complaint submitted successfully.",
                "tracking_id": complaint.tracking_id,
                "complaint": ComplaintDetailSerializer(complaint).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ComplaintDetailView(APIView):
    """
    GET   /api/v1/complaints/<id>/   — detail
    PATCH /api/v1/complaints/<id>/   — owner or admin update description/location
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerOrAdmin()]

    def _get_complaint(self, pk):
        return get_object_or_404(
            Complaint.objects.select_related("category", "assigned_to", "user")
            .prefetch_related("attachments", "status_history"),
            pk=pk,
        )

    def get(self, request, pk):
        complaint = self._get_complaint(pk)
        Complaint.objects.filter(pk=pk).update(view_count=complaint.view_count + 1)
        return Response(ComplaintDetailSerializer(complaint).data)

    def patch(self, request, pk):
        complaint = self._get_complaint(pk)
        self.check_object_permissions(request, complaint)
        allowed_fields = ["description", "title", "address", "latitude", "longitude", "city", "ward", "pincode"]
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        for field, value in data.items():
            if field in ("latitude", "longitude") and value not in (None, ""):
                try:
                    value = quantize_lat_lng(value)
                except SerializerValidationError as exc:
                    return Response({field: exc.detail}, status=status.HTTP_400_BAD_REQUEST)
            setattr(complaint, field, value)
        complaint.save()
        return Response(ComplaintDetailSerializer(complaint).data)


class TrackComplaintView(APIView):
    """GET /api/v1/complaints/track/<tracking_id>/ — public tracking by ticket ID"""

    permission_classes = [AllowAny]

    def get(self, request, tracking_id):
        complaint = get_object_or_404(
            Complaint.objects.select_related("category")
            .prefetch_related("status_history"),
            tracking_id=tracking_id,
        )
        return Response(
            {
                "tracking_id": complaint.tracking_id,
                "status": complaint.status,
                "category": complaint.category.name if complaint.category else None,
                "city": complaint.city,
                "created_at": complaint.created_at,
                "updated_at": complaint.updated_at,
                "resolved_at": complaint.resolved_at,
                "status_history": [
                    {
                        "status": h.new_status,
                        "note": h.note,
                        "date": h.created_at,
                    }
                    for h in complaint.status_history.order_by("created_at")
                ],
            }
        )


class ComplaintStatusUpdateView(APIView):
    """PATCH /api/v1/complaints/<id>/status/ — officer/admin updates status"""

    permission_classes = [IsAuthenticated, IsOfficer]

    def patch(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        serializer = ComplaintStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint = update_complaint_status(
            complaint=complaint,
            new_status=serializer.validated_data["status"],
            changed_by=request.user,
            note=serializer.validated_data.get("note", ""),
            priority=serializer.validated_data.get("priority"),
        )
        return Response(
            {
                "message": "Status updated.",
                "tracking_id": complaint.tracking_id,
                "status": complaint.status,
            }
        )


class ComplaintAssignView(APIView):
    """POST /api/v1/complaints/<id>/assign/ — admin assigns complaint to officer"""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        serializer = ComplaintAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            complaint = assign_complaint(
                complaint=complaint,
                officer_id=serializer.validated_data["officer_id"],
                due_date=serializer.validated_data.get("due_date"),
                assigned_by=request.user,
            )
        except ValueError as e:
            return Response(
                {"error": {"code": "bad_request", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"message": "Complaint assigned.", "assigned_to": str(complaint.assigned_to)})


class ComplaintUpvoteView(APIView):
    """POST /api/v1/complaints/<id>/upvote/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        count = upvote_complaint(complaint, request.user)
        return Response({"upvote_count": count})


class ComplaintStatsView(APIView):
    """GET /api/v1/complaints/stats/ — admin/officer dashboard aggregates"""

    permission_classes = [IsAuthenticated, IsOfficer]

    def get(self, request):
        qs = Complaint.objects.all()
        if request.user.role == "officer":
            qs = qs.filter(assigned_to=request.user)
        stats = get_complaint_stats(qs)
        return Response(stats)


class MyComplaintsView(APIView):
    """GET /api/v1/complaints/mine/ — citizen's own complaints"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Complaint.objects.filter(user=request.user).select_related("category")
        filterset = ComplaintFilter(request.GET, queryset=qs)
        filterset.is_valid()

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(filterset.qs, request)
        return paginator.get_paginated_response(ComplaintListSerializer(page, many=True).data)


class ComplaintDuplicateCheckView(APIView):
    """
    GET  /api/v1/complaints/check-duplicates/?description=...&city=...&ward=...
    POST /api/v1/complaints/check-duplicates/  body: { description, city?, ward? }
    POST avoids very long descriptions breaking URL limits in browsers / proxies.
    """

    permission_classes = [IsAuthenticated]

    def _respond(self, desc: str, city: str, ward: str):
        qs = find_similar_complaints(desc, city=city, ward=ward, limit=8)
        data = ComplaintListSerializer(qs, many=True).data
        return Response({"possible_duplicates": data, "count": len(data)})

    def get(self, request):
        return self._respond(
            request.GET.get("description", ""),
            request.GET.get("city", ""),
            request.GET.get("ward", ""),
        )

    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        return self._respond(
            (body.get("description") or "").strip(),
            (body.get("city") or "").strip(),
            (body.get("ward") or "").strip(),
        )


class ComplaintHintsView(APIView):
    """GET /api/v1/complaints/hints/?category_id=&city= — past resolved similar (demo)."""

    permission_classes = [AllowAny]

    def get(self, request):
        cid = request.GET.get("category_id")
        city = request.GET.get("city", "")
        cat_id = int(cid) if cid and str(cid).isdigit() else None
        qs = past_resolutions(category_id=cat_id, city=city, limit=6)
        rows = [
            {
                "tracking_id": c.tracking_id,
                "title": c.title,
                "category": c.category.name if c.category else None,
                "city": c.city,
                "resolved_at": c.resolved_at,
                "note": "Similar issue was resolved earlier (demo suggestion).",
            }
            for c in qs
        ]
        return Response({"suggestions": rows})


class ComplaintSLAView(APIView):
    """GET /api/v1/complaints/<uuid>/sla/ — legacy + Phase 2 prediction (public)."""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        complaint = get_object_or_404(Complaint.objects.select_related("category"), pk=pk)
        legacy = sla_estimate(complaint)
        phase2 = predict_sla_full(complaint)
        return Response(
            {
                **legacy,
                "phase2_prediction": phase2,
            }
        )


class ComplaintClusterListView(APIView):
    """GET /api/v1/complaints/clusters/<cluster_key>/ — same-area duplicate cluster members."""

    permission_classes = [IsAuthenticated]

    def get(self, request, cluster_key):
        if not cluster_key or len(cluster_key) < 8:
            return Response(
                {"error": {"code": "bad_request", "message": "Invalid cluster key."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = find_cluster_complaints(cluster_key)
        return Response(
            {
                "cluster_key": cluster_key,
                "count": qs.count(),
                "complaints": ComplaintListSerializer(qs[:50], many=True).data,
            }
        )


class IssueVerificationView(APIView):
    """POST /api/v1/complaints/<uuid>/verify/ — community confirmation (one per user)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        if complaint.user_id == request.user.id:
            return Response(
                {"error": {"code": "bad_request", "message": "You cannot verify your own report."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj, created = IssueVerification.objects.get_or_create(
            complaint=complaint, user=request.user
        )
        if created:
            Complaint.objects.filter(pk=complaint.pk).update(
                verification_count=F("verification_count") + 1
            )
        complaint.refresh_from_db(fields=["verification_count"])
        return Response(
            {
                "verified": True,
                "already_verified": not created,
                "verification_count": complaint.verification_count,
            },
            status=status.HTTP_200_OK,
        )


class AssignmentSuggestionView(APIView):
    """GET /api/v1/complaints/<uuid>/assignment-suggestion/ — Phase 2 routing preview."""

    permission_classes = [IsAuthenticated, IsOfficer]

    def get(self, request, pk):
        complaint = get_object_or_404(Complaint.objects.select_related("category"), pk=pk)
        officer = suggest_assignee(complaint)
        if not officer:
            return Response({"officer": None, "note": "No eligible officer in directory."})
        from apps.accounts.serializers import UserSerializer

        return Response(
            {
                "officer": UserSerializer(officer).data,
                "open_assignment_load": officer.assigned_complaints.filter(
                    status__in=("submitted", "acknowledged", "in_progress")
                ).count(),
            }
        )


class SentimentTrendsView(APIView):
    """GET /api/v1/complaints/analytics/sentiment/?days=14 — dashboard series."""

    permission_classes = [IsAuthenticated, IsOfficer]

    def get(self, request):
        try:
            days = int(request.GET.get("days", "14"))
        except ValueError:
            days = 14
        days = max(7, min(90, days))
        return Response({"days": days, "series": sentiment_trend_series(days)})


class GeoReverseView(APIView):
    """
    GET /api/v1/complaints/geo/reverse/?lat=&lng=
    Uses OpenStreetMap Nominatim (demo; respect usage policy in production).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        lat = request.GET.get("lat")
        lng = request.GET.get("lng")
        if not lat or not lng:
            return Response(
                {"error": {"code": "bad_request", "message": "lat and lng are required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            la = float(lat)
            lo = float(lng)
        except ValueError:
            return Response(
                {"error": {"code": "bad_request", "message": "Invalid coordinates."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        display_name = ""
        try:
            import json
            import urllib.error
            import urllib.request

            url = f"https://nominatim.openstreetmap.org/reverse?lat={la}&lon={lo}&format=json"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": getattr(settings, "NOMINATIM_USER_AGENT", "NagrikAwaazDemo/1.0 (college project)")},
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                payload = json.loads(resp.read().decode())
                display_name = payload.get("display_name", "") or ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("Geo reverse failed: %s", exc)
            display_name = ""

        return Response(
            {
                "latitude": la,
                "longitude": lo,
                "display_name": display_name or f"{la:.5f}, {lo:.5f}",
            }
        )


class GeoIpView(APIView):
    """
    GET /api/v1/complaints/geo/ip/
    Approximate location from client IP when device GPS is unavailable (demo fallback).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
        ip = forwarded.split(",")[0].strip() if forwarded else (request.META.get("REMOTE_ADDR") or "")

        if ip in ("127.0.0.1", "::1", "localhost") or ip.startswith(("192.168.", "10.", "172.")):
            la, lo = 30.3165, 78.0322
            return Response(
                {
                    "latitude": la,
                    "longitude": lo,
                    "display_name": "Dehradun, Uttarakhand, India (approximate — local dev)",
                    "accuracy": "approximate",
                    "source": "demo_local",
                }
            )

        try:
            import json
            import urllib.request

            url = f"http://ip-api.com/json/{ip}?fields=status,message,lat,lon,city,regionName,country"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": getattr(settings, "NOMINATIM_USER_AGENT", "NagrikAwaazDemo/1.0 (college project)")},
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())
            if data.get("status") != "success":
                raise ValueError(data.get("message", "IP lookup failed"))
            la = float(data["lat"])
            lo = float(data["lon"])
            parts = [p for p in [data.get("city"), data.get("regionName"), data.get("country")] if p]
            display = ", ".join(parts) + " (approximate — network)"
            return Response(
                {
                    "latitude": la,
                    "longitude": lo,
                    "display_name": display,
                    "accuracy": "approximate",
                    "source": "ip",
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Geo IP lookup failed: %s", exc)
            return Response(
                {"error": {"code": "geo_unavailable", "message": "Could not determine approximate location."}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
