"""Shared pieces the stages depend on, that are not themselves stages."""

from services.asyncapply.stages.utils.outputs import (
    Contact,
    CoverLetter,
    CvTailoring,
    Evaluation,
    EvaluationDraft,
    Extraction,
    SearchQueries,
    Shortlist,
)

__all__ = [
    "Contact",
    "CoverLetter",
    "CvTailoring",
    "Evaluation",
    "EvaluationDraft",
    "Extraction",
    "SearchQueries",
    "Shortlist",
]
