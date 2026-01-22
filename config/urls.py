from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Clinic Topics API",
        default_version="v1",
        description="API for Clinic Topics backend",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="nishant.kumar@qsstechnosoft.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

def home(request):
    return JsonResponse({
        "message": "Welcome to Clinic Topics API",
        "docs": "/swagger/",
        "admin": "/admin/",
        "redoc": "/redoc/",
    })

urlpatterns = [
    path("", home),

    # API Documentation
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),

    # Django Admin
    path("admin/", admin.site.urls),

    # Include app URLs under a clean prefix 
    path("api/v1/auth/", include(("apps.accounts.urls", "accounts"), namespace="accounts")),
    path("api/v1/profiles/", include(("apps.profiles.urls", "profiles"), namespace="profiles")),
    path("api/v1/commerce/", include(("apps.commerce.urls", "commerce"), namespace="commerce")),
    path("api/v1/events/", include(("apps.events.urls", "events"), namespace="events")),
    path("api/v1/topics/", include(("apps.topics.urls", "topics"), namespace="topics")),
    path("api/v1/analytics/", include(("apps.analytics.urls", "analytics"), namespace="analytics")),
    path("api/v1/cms/", include(("apps.cms.urls", "cms"), namespace="cms")),
    path("api/v1/advertisements/", include(("apps.advertisements.urls", "advertisements"), namespace="advertisements")),
    path("api/v1/", include(("apps.IDI.urls", "idi"), namespace="idi")),
    path("api/v1/", include(("apps.advisory.urls", "advisory"), namespace="advisory")),
    path("api/v1/second-opinion/", include(("apps.second_opinion.urls", "second_opinion"), namespace="second_opinion")),
    path("api/v1/appointments/", include(("apps.appointments.urls", "appointments"), namespace="appointments")),
    path("api/v1/video-calls/", include(("apps.video_calls.urls", "video_calls"), namespace="video_calls")),
    path("api/v1/report-template/", include(("apps.report_template.urls", "report_template"), namespace="report_template")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
