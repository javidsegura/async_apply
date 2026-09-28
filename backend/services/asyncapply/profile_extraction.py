"""Best-effort fill of a profile form from an uploaded CV PDF.

One schema-constrained call, same machinery as the pipeline's own stages
(llm.ask), reused here for a one-off setup task rather than per-application
work. The "extract_jd" stage's model is reused rather than adding a new
settings column: this is the same shape of task (pull structured facts out
of unstructured text), just run once at profile setup instead of per posting.
"""

from services.asyncapply.context.loader import load_mode
from services.asyncapply.llm import ask
from services.asyncapply.profile_schema import ExtractedProfile
from services.asyncapply.utils.documents.cv_reader import extract_cv_text_and_links

_EXTRACTION_STAGE = "extract_jd"


async def extract_profile_from_cv(pdf_bytes: bytes) -> ExtractedProfile:
    """Read a CV PDF and return the fields it can fill in, best effort.

    Args:
        pdf_bytes: The raw uploaded CV file.

    Returns:
        The AI-fillable subset of the profile. Anything not stated on the
        CV comes back null or empty -- the caller merges this into the
        user's form rather than trusting it as the final answer.
    """
    text, links = extract_cv_text_and_links(pdf_bytes)

    system_prompt = load_mode("extract_profile")
    user_prompt = (
        f"## CV text\n{text}\n\n"
        f"## Links found on the page (match these to linkedin/github/portfolio_url)\n"
        + "\n".join(links)
    )

    return await ask(_EXTRACTION_STAGE, system_prompt, user_prompt, ExtractedProfile)
