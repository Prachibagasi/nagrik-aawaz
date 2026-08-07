from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .storage import add_complaint, load_complaints

VALID_DEPTS = {"bijli", "jal", "pwd", "shiksha"}


class DepartmentComplaintListCreateView(APIView):
    """
    GET/POST /api/v1/departments/{dept}/complaints/
    Public demo API consumed by dummy department websites and Nagrik Awaaz routing.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, dept_key: str):
        if dept_key not in VALID_DEPTS:
            return Response(
                {"error": {"code": "not_found", "message": f"Unknown department '{dept_key}'."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(load_complaints(dept_key))

    def post(self, request, dept_key: str):
        if dept_key not in VALID_DEPTS:
            return Response(
                {"error": {"code": "not_found", "message": f"Unknown department '{dept_key}'."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        body = request.data if isinstance(request.data, dict) else {}
        item = add_complaint(dept_key, body)
        return Response(item, status=status.HTTP_201_CREATED)


class DepartmentPortalInfoView(APIView):
    """GET /api/v1/departments/portals/ — portal URLs for the web app."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        from apps.ai_ml.services.agent1_config import department_portal_config, portal_base

        return Response({
            "portal_base": portal_base(),
            "departments": {
                key: department_portal_config(key)
                for key in ("Electricity", "Water", "PWD", "Education", "Other")
            },
        })
