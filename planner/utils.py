from io import BytesIO

from django.template.loader import get_template
from xhtml2pdf import pisa


def render_to_pdf(template_src, context):
    """
    Render a Django template to PDF bytes using xhtml2pdf.
    Returns bytes on success, or None on error.
    """
    template = get_template(template_src)
    html = template.render(context)
    result = BytesIO()

    pdf = pisa.CreatePDF(html, dest=result)
    if pdf.err:
        return None

    return result.getvalue()

