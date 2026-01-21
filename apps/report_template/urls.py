from django.urls import path
from apps.report_template.views import ReportTemplateView, GenerateSecondOpinionReportView

urlpatterns = [
    path("", ReportTemplateView.as_view(), name="report-template"),
    path("generate/<uuid:doctor_request_id>/", GenerateSecondOpinionReportView.as_view(), name="generate-second-opinion-report"),
]
