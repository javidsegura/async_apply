"""Prints the filled CV and cover-letter HTML to PDF."""

from pathlib import Path

from services.asyncapply.utils.chromium import open_page


async def render_pdf(html_content: str, output_path: Path) -> Path:
    """Write one HTML string out as a PDF.

    Args:
        html_content: Fully-resolved HTML.
        output_path: Where to write the PDF; parent directories are created.

    Returns:
        The output path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with open_page() as page:
        await page.set_content(html_content)
        await page.pdf(path=str(output_path), print_background=True)
    return output_path
