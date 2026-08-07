from django.urls import path

from . import views

urlpatterns = [
    path("portals/", views.DepartmentPortalInfoView.as_view(), name="dept-portals"),
    path("<str:dept_key>/complaints/", views.DepartmentComplaintListCreateView.as_view(), name="dept-complaints"),
]
