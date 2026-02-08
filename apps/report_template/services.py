import os
from django.template import Template, Context
if os.getenv("ENVIRONMENT") != "development":
    from weasyprint import HTML
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import datetime

from apps.report_template.templates.report import get_report_template_string


class ReportPDFService:
    @staticmethod
    def generate_pdf(template_data: dict) -> str:
        template_string = get_report_template_string()
        template = Template(template_string)
        html_content = template.render(Context(template_data))
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"reports/second_opinion_report_{template_data['patient_id']}_{timestamp}.pdf"
        pdf_bytes = HTML(string=html_content, base_url=settings.MEDIA_ROOT).write_pdf()
        saved_path = default_storage.save(pdf_filename, ContentFile(pdf_bytes))
        return default_storage.url(saved_path)


def calculate_age(birth_date):
    if not birth_date: return None
    today = datetime.date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

