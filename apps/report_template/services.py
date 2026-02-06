import os, tempfile
from django.template import Template, Context
if os.getenv('ENVIRONMENT') == 'development':
    from pyhtml2pdf import converter
else: from weasyprint import HTML
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import datetime

from apps.report_template.templates.report import get_report_template_string


class ReportPDFService:
    @staticmethod
    def generate_pdf(template_data: dict) -> str:
        """
        Generate a PDF report and save it to the default storage.
        Returns the URL to access the PDF.
        """
        template_string = get_report_template_string()
        template = Template(template_string)
        html_content = template.render(Context(template_data))

        # Generate unique filename with timestamp to avoid caching issues
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"reports/second_opinion_report_{template_data['patient_id']}_{timestamp}.pdf"

        if os.getenv('ENVIRONMENT') == 'development':
            # Development: Use local file system with pyhtml2pdf
            pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_filename)
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as html_file:
                html_file.write(html_content.encode("utf-8"))
                html_path = html_file.name

            converter.convert(f"file:///{html_path}", pdf_path)
            os.remove(html_path)
            
            # Return local media URL for development
            return f"{settings.MEDIA_URL}{pdf_filename}"
        else:
            # Production: Generate PDF and upload to default storage (S3)
            pdf_bytes = HTML(string=html_content, base_url=settings.MEDIA_ROOT).write_pdf()
            
            # Save to default storage (S3 in production)
            saved_path = default_storage.save(pdf_filename, ContentFile(pdf_bytes))
            
            # Return the URL (signed URL if querystring_auth is True)
            return default_storage.url(saved_path)


def calculate_age(birth_date):
    if not birth_date: return None
    today = datetime.date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

