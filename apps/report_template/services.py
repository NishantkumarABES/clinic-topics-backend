import os
from django.template import Template, Context
from weasyprint import HTML
from django.conf import settings
import datetime

from apps.report_template.templates.report import get_report_template_string


# class ReportPDFService:
#     @staticmethod
#     def generate_pdf(template_data: dict) -> str:
#         template_string = get_report_template_string()  
#         template = Template(template_string)
#         html_content = template.render(Context(template_data))

#         # Create temporary HTML file
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as html_file:
#             html_file.write(html_content.encode("utf-8"))
#             html_path = html_file.name

#         # Output PDF path
#         pdf_filename = f"second_opinion_report_{template_data['patient_id']}.pdf"
#         pdf_path = os.path.join(settings.MEDIA_ROOT, "reports", pdf_filename)
#         os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
#         # Convert HTML → PDF
#         converter.convert(f"file:///{html_path}", pdf_path)
#         # Cleanup temp html
#         os.remove(html_path)
#         return pdf_path


class ReportPDFService:
    @staticmethod
    def generate_pdf(template_data: dict) -> str:
        template_string = get_report_template_string()
        template = Template(template_string)
        html_content = template.render(Context(template_data))

        # Output PDF path
        pdf_filename = f"second_opinion_report_{template_data['patient_id']}.pdf"
        pdf_path = os.path.join(settings.MEDIA_ROOT, "reports", pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        # Generate PDF directly from HTML string
        HTML(string=html_content, base_url=settings.MEDIA_ROOT).write_pdf(pdf_path)

        return pdf_path


def calculate_age(birth_date):
    if not birth_date: return None
    today = datetime.date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

