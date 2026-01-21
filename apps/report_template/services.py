import os
import tempfile
from django.template.loader import render_to_string
from django.conf import settings
from pyhtml2pdf import converter


class ReportPDFService:
    @staticmethod
    def generate_pdf(template_data: dict) -> str:
        html_content = render_to_string(
            "report_template/report.html", template_data
        )

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as html_file:
            html_file.write(html_content.encode("utf-8"))
            html_path = html_file.name

        # Output PDF path
        pdf_filename = f"second_opinion_report_{template_data['patient_id']}.pdf"
        pdf_path = os.path.join(settings.MEDIA_ROOT, "reports", pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        # Convert HTML → PDF
        converter.convert(f"file:///{html_path}", pdf_path)
        # Cleanup temp html
        os.remove(html_path)
        return pdf_path


