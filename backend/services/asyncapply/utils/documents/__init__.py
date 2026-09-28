"""Turning an evaluation into the tailored CV and cover-letter PDFs."""

from services.asyncapply.utils.documents.fit import fit_cv
from services.asyncapply.utils.documents.html import build_cover_letter, build_cv
from services.asyncapply.utils.documents.pdf import render_pdf

__all__ = ["build_cover_letter", "build_cv", "fit_cv", "render_pdf"]
