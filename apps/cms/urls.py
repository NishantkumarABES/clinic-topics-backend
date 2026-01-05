from django.urls import path
from apps.cms.views import StaticPageView, AdminStaticPageUpdateView, AdminPublishStaticPageView

urlpatterns = [
    # Public
    path("pages/<str:page_type>/", StaticPageView.as_view()),

    # Admin CMS
    path("admin/pages/<str:page_type>/update/", AdminStaticPageUpdateView.as_view()),
    path("admin/pages/version/<uuid:version_id>/publish/", AdminPublishStaticPageView.as_view()),
]