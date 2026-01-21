from django.urls import path
from apps.report_template.views import ReportTemplateView

urlpatterns = [
    path("", ReportTemplateView.as_view(), name="report-template"),
]
