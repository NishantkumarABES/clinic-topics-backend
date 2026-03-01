from django.urls import path
from apps.cms.views import (
    StaticPageView, ContactUsSubmitView, AdminSettingsListView, AdminSettingDetailView, AdminSettingVersionsView,
    AdminPublishVersionView, AdminContactListView, AdminContactUpdateView, AdminSiteConfigurationView,
)

urlpatterns = [
    # Public endpoints
    path("pages/<str:page_type>/", StaticPageView.as_view(), name="static-page"),
    path("contact/submit/", ContactUsSubmitView.as_view(), name="contact-submit"),

    # Admin Settings endpoints
    path("admin/settings/", AdminSettingsListView.as_view(), name="admin-settings-list"),
    path("admin/settings/<str:page_type>/", AdminSettingDetailView.as_view(), name="admin-setting-detail"),
    path("admin/settings/<str:page_type>/versions/", AdminSettingVersionsView.as_view(), name="admin-setting-versions"),
    path("admin/versions/<uuid:version_id>/publish/", AdminPublishVersionView.as_view(), name="admin-publish-version"),

    # Admin Site Configuration endpoints
    path("admin/site-configuration/", AdminSiteConfigurationView.as_view(), name="admin-site-configuration"),

    # Admin Contact endpoints
    path("admin/contacts/", AdminContactListView.as_view(), name="admin-contact-list"),
    path("admin/contacts/<uuid:contact_id>/", AdminContactUpdateView.as_view(), name="admin-contact-update"),
]