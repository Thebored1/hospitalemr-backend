from __future__ import annotations

import os
from io import BytesIO

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import get_template


def _link_callback(uri: str, rel: str | None = None) -> str:
    """
    Convert HTML asset URIs to absolute filesystem paths for PDF generation.

    Supports:
    - STATIC_URL -> files in STATICFILES_DIRS / app static via staticfiles finders
    - MEDIA_URL -> files under MEDIA_ROOT
    """
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.removeprefix(settings.MEDIA_URL))
        if os.path.isfile(path):
            return path

    if uri.startswith(settings.STATIC_URL):
        static_path = uri.removeprefix(settings.STATIC_URL)
        found = finders.find(static_path)
        if found:
            # `find` may return a list when multiple are found.
            if isinstance(found, (list, tuple)):
                found = found[0]
            return found

        # Best-effort fallback when STATIC_ROOT is used.
        if getattr(settings, "STATIC_ROOT", None):
            path = os.path.join(settings.STATIC_ROOT, static_path)
            if os.path.isfile(path):
                return path

    # Let xhtml2pdf try to resolve it (or fail with a useful error).
    return uri


def render_pdf_response(*, template_name: str, context: dict, filename: str) -> HttpResponse:
    """
    Render a Django template to a downloadable PDF using xhtml2pdf.
    """
    try:
        from xhtml2pdf import pisa
    except Exception as exc:  # pragma: no cover
        return HttpResponse(
            "PDF generation is not available (missing dependency xhtml2pdf).",
            status=501,
            content_type="text/plain",
        )

    template = get_template(template_name)
    html = template.render(context)

    result = BytesIO()
    pdf = pisa.CreatePDF(
        src=BytesIO(html.encode("utf-8")),
        dest=result,
        encoding="utf-8",
        link_callback=_link_callback,
    )
    if pdf.err:
        return HttpResponse(
            "Could not generate PDF.",
            status=500,
            content_type="text/plain",
        )

    response = HttpResponse(result.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

