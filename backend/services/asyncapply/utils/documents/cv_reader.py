"""Reads a candidate-uploaded CV PDF back into plain text, for the AI-fill
step in the profile form -- the one place this app reads a PDF instead of
writing one.
"""

import io

from pypdf import PdfReader

# A PDF page's real text often mangles hyperlink anchors down to their
# visible label ("LinkedIn", "Github", "Portfolio"), with the actual URL
# living only in the page's link annotations. Both matter: the extraction
# prompt is given the text for everything else, plus this list so it can
# match a URL to whichever contact field it plausibly belongs to.
_MAILTO_PREFIX = "mailto:"


def extract_cv_text_and_links(pdf_bytes: bytes) -> tuple[str, list[str]]:
    """Pull the visible text and every hyperlink target out of a CV PDF.

    Args:
        pdf_bytes: The raw uploaded file.

    Returns:
        (text, links) -- the concatenated page text, and the deduplicated
        list of http(s) URLs found in link annotations (mailto: links are
        dropped, since the email address is already in the visible text).
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))

    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    links: list[str] = []
    for page in reader.pages:
        annotations = page.get("/Annots")
        if not annotations:
            continue
        for annotation in annotations:
            obj = annotation.get_object()
            action = obj.get("/A")
            uri = action.get("/URI") if action else None
            if uri and not uri.startswith(_MAILTO_PREFIX) and uri not in links:
                links.append(uri)

    return text, links
