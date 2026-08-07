import django_filters
from .models import Complaint


class ComplaintFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=Complaint.STATUS_CHOICES)
    priority = django_filters.MultipleChoiceFilter(choices=Complaint.PRIORITY_CHOICES)
    city = django_filters.CharFilter(lookup_expr="icontains")
    ward = django_filters.CharFilter(lookup_expr="icontains")
    category = django_filters.NumberFilter(field_name="category__id")
    source = django_filters.ChoiceFilter(choices=Complaint.SOURCE_CHOICES)
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    assigned_to = django_filters.UUIDFilter(field_name="assigned_to__id")
    is_anonymous = django_filters.BooleanFilter()
    is_duplicate = django_filters.BooleanFilter()

    class Meta:
        model = Complaint
        fields = [
            "status", "priority", "city", "ward", "category",
            "source", "is_anonymous", "is_duplicate",
            "assigned_to", "created_after", "created_before",
        ]
