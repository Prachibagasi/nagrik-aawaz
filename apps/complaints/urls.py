from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path("categories/",                      views.CategoryListView.as_view(),         name="category-list"),

    # Demo / college: duplicates, hints, geo (before <uuid:pk> routes)
    path("check-duplicates/",                 views.ComplaintDuplicateCheckView.as_view(), name="complaint-duplicates"),
    path("hints/",                            views.ComplaintHintsView.as_view(),            name="complaint-hints"),
    path("geo/reverse/",                      views.GeoReverseView.as_view(),                name="geo-reverse"),
    path("geo/ip/",                           views.GeoIpView.as_view(),                     name="geo-ip"),

    # Phase 2
    path("clusters/<str:cluster_key>/",       views.ComplaintClusterListView.as_view(),      name="complaint-cluster-list"),
    path("analytics/sentiment/",               views.SentimentTrendsView.as_view(),           name="complaint-sentiment-analytics"),

    # Complaints CRUD
    path("",                                 views.ComplaintListCreateView.as_view(),  name="complaint-list-create"),
    path("<uuid:pk>/",                       views.ComplaintDetailView.as_view(),      name="complaint-detail"),

    # Workflow
    path("<uuid:pk>/status/",               views.ComplaintStatusUpdateView.as_view(), name="complaint-status-update"),
    path("<uuid:pk>/assign/",               views.ComplaintAssignView.as_view(),       name="complaint-assign"),
    path("<uuid:pk>/upvote/",               views.ComplaintUpvoteView.as_view(),       name="complaint-upvote"),
    path("<uuid:pk>/sla/",                  views.ComplaintSLAView.as_view(),            name="complaint-sla"),
    path("<uuid:pk>/verify/",               views.IssueVerificationView.as_view(),      name="complaint-verify"),
    path("<uuid:pk>/assignment-suggestion/", views.AssignmentSuggestionView.as_view(),   name="complaint-assign-suggest"),

    # Public tracking
    path("track/<str:tracking_id>/",         views.TrackComplaintView.as_view(),       name="complaint-track"),

    # Dashboard
    path("stats/",                           views.ComplaintStatsView.as_view(),       name="complaint-stats"),
    path("mine/",                            views.MyComplaintsView.as_view(),         name="complaint-mine"),
]
