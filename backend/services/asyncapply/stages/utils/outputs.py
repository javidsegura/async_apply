"""What each stage is contracted to return.

These are the schemas the provider validates against and the types the worker
reads, so a field can only be renamed in one place.

Two conventions worth knowing:

- Every field carries a description. Those descriptions are part of the JSON
  schema sent with the request, so the model reads them: they are instructions,
  not comments, and they are the right place for per-field rules.
- Anything with a fixed vocabulary is a Literal, which becomes an enum the
  provider enforces. That stops the same idea arriving as "Startup", "start-up"
  and "early stage" on three different runs.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CompanyType = Literal[
    "start_up", "scale_up", "big_tech", "big_finance", "enterprise", "mid_size_regional"
]
Legitimacy = Literal["high_confidence", "proceed_with_caution", "suspicious"]
WorkAuthTier = Literal["sponsors", "not_needed", "unstated", "no_sponsorship"]
ContactType = Literal["recruiter", "hiring_manager", "peer", "interviewer"]


class StageOutput(BaseModel):
    """Base for stage results: reject unexpected keys rather than ignore them."""

    model_config = ConfigDict(extra="forbid")


class Extraction(StageOutput):
    """What extract_jd returns."""

    extraction_failed: bool = Field(
        description="True when no real job description could be read from the input."
    )
    jd_text: str | None = Field(
        default=None,
        description="The full job description text, verbatim. Null when extraction failed.",
    )
    reason: str | None = Field(
        default=None,
        description="What was tried and why it failed. Null when extraction succeeded.",
    )



class CvTailoring(StageOutput):
    """The two things that change per posting.

    Everything else on the page - identity, education, experience, projects,
    awards, activities - is a fact and comes from the profile verbatim. This
    only decides which projects appear and in what order the technologies read.
    """

    projects: list[str] = Field(
        default_factory=list,
        description=(
            "Headings of the two most relevant projects, copied exactly from "
            "cv.projects in the profile, best first. Only two reach the page, so "
            "choose. A heading that is not in the profile is ignored."
        ),
    )
    technologies: list[str] = Field(
        default_factory=list,
        description=(
            "The entries of cv.technologies, reordered so the ones this posting "
            "names come first. This is the main ATS keyword match: keep the "
            "profile's exact spelling, and never add one it does not list."
        ),
    )

# Well under the 350-450 target: only a genuinely stunted letter should
# cost a retry, not ordinary variance around the asked-for length.
MIN_BODY_WORDS = 280


class CoverLetter(StageOutput):
    """The body of a cover letter.

    Unlike the CV, a letter is prose and no ATS parses it structurally, so the
    model writes the argument freely. Everything around it - the candidate's
    name and contacts, the date, the company line, the greeting and the
    sign-off - is fixed by the template.
    """

    paragraphs: list[str] = Field(
        default_factory=list,
        description=(
            "The letter body: exactly five paragraphs of 70-90 words each, "
            "350-450 words in total. Write full paragraphs -- anything under 60 "
            "words is a stub and reads as an afterthought, and the total is "
            "checked, so count as you go. No greeting and no sign-off. "
            "(1) The role and why this company specifically. "
            "(2) The strongest concrete win from the CV that matches this "
            "posting, with its metrics exactly as written. "
            "(3) A second, different angle -- another project or responsibility "
            "that covers a requirement the first paragraph did not. "
            "(4) A third angle -- a skill, a piece of domain knowledge, or a "
            "collaboration/leadership moment the first two paragraphs did not "
            "already cover. "
            "(5) How the candidate's trajectory fits what this role needs, then "
            "logistics (availability, work authorization, relocation if "
            "relevant) and a clear ask. "
            "No markdown, no bullet lists, no headings."
        ),
    )

    @model_validator(mode="after")
    def _require_substance(self) -> "CoverLetter":
        """Reject a letter far below the asked-for length.

        The prompt has asked for 250+ words through several revisions and
        models still return ~180, so the floor is enforced here where it
        cannot be ignored: a short reply fails validation, which feeds the
        model its own answer plus this error and asks again. Set well under
        the 280-340 target rather than at it, so ordinary variance passes and
        only a genuinely stunted letter costs a retry.

        Returns:
            The letter, when it carries enough prose to be worth sending.

        Raises:
            ValueError: if the body is shorter than MIN_BODY_WORDS.
        """
        words = sum(len(p.split()) for p in self.paragraphs)
        if words < MIN_BODY_WORDS:
            raise ValueError(
                f"the cover letter body is {words} words; it must be at least "
                f"{MIN_BODY_WORDS} (target 350-450). Expand each paragraph with "
                "specifics from the CV rather than adding new paragraphs."
            )
        return self


SecurityClearance = Literal["none", "citizenship_required", "clearance_required"]


class EvaluationDraft(StageOutput):
    """What the model returns for evaluate_job.

    There is deliberately no free-text hard-stop field here. A model asked to
    both judge and narrate a disqualification treats the narration as scratch
    space: it writes a paragraph concluding no stop should fire, then sets the
    field anyway, or infers a stop from an office address with nothing in the
    posting to back it. So the model only reports grounded facts -- each
    disqualifying claim paired with the exact line that supports it -- and
    evaluate_job.py decides pass/fail from those facts in Python, the same way
    it is decided for every run rather than reworded by the model each time.

    cv_tailoring and cover_letter are required, not conditional on a stop: the
    model always writes them, and evaluate_job.py discards them if a rule
    fires. That removes the retry this stage used to need when a wrongly
    guessed stop was cleared but had already skipped writing the documents.
    """

    company: str | None = Field(default=None, description="Hiring company name.")
    role: str | None = Field(default=None, description="Job title as the posting states it.")
    location: str | None = Field(
        default=None,
        description=(
            "The role's own location as the posting states it, e.g. 'Madrid, Spain' or "
            "'Remote (US)'. Used to target outreach searches at the right office/region -- "
            "not the same question as outside_authorized_countries below."
        ),
    )
    company_type: CompanyType | None = Field(
        default=None, description="Company category. Null when the posting gives no signal."
    )
    score: float | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Fit from 1 to 5, judged from the CV against this posting.",
    )
    strengths: list[str] = Field(
        default_factory=list, description="The two strongest CV-to-posting matches."
    )
    gaps: list[str] = Field(
        default_factory=list, description="The two gaps that matter most for this role."
    )
    legitimacy: Legitimacy | None = Field(
        default=None,
        description="How real the posting looks, from its specificity and internal consistency.",
    )
    outside_authorized_countries: bool = Field(
        description=(
            "Whether this role's location is outside every country in the candidate's "
            "authorized_in list (which already includes the EU/EEA and Switzerland as a "
            "bloc, not just the candidate's home country -- so an EU posting is never "
            "outside it). A pure geography question, answered independent of sponsorship."
        )
    )
    work_auth_tier: WorkAuthTier = Field(
        description="The posting's own stated sponsorship stance. 'unstated' is the common case."
    )
    work_auth_quote: str | None = Field(
        default=None,
        description=(
            "Required when work_auth_tier is 'no_sponsorship': the posting's refusal, copied "
            "word for word. It is checked against the posting text, so a paraphrase or an "
            "inference from the office location is rejected and the tier is not trusted."
        ),
    )
    security_clearance: SecurityClearance = Field(
        default="none",
        description=(
            "'citizenship_required' when the posting demands a specific citizenship (e.g. "
            "'must be a US citizen'). 'clearance_required' for an existing government "
            "security clearance. 'none' otherwise -- an ordinary background check is not this."
        ),
    )
    clearance_quote: str | None = Field(
        default=None,
        description=(
            "Required when security_clearance is not 'none': the posting's own line, copied "
            "word for word. Checked the same way as work_auth_quote."
        ),
    )
    min_years_required: int | None = Field(
        default=None,
        description="A stated minimum years of experience, if the posting names one. Informational only.",
    )
    verdict: str = Field(
        description="Three to five sentences: top strength, top gap, then a recommendation."
    )
    cv_tailoring: CvTailoring
    cover_letter: CoverLetter


class Evaluation(StageOutput):
    """The stored result of evaluate_job: EvaluationDraft plus the hard-stop
    verdict evaluate_job.py computed from it, with assets dropped if it fired."""

    company: str | None = None
    role: str | None = None
    location: str | None = None
    company_type: CompanyType | None = None
    score: float | None = None
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    legitimacy: Legitimacy | None = None
    work_auth_tier: WorkAuthTier | None = None
    min_years_required: int | None = None
    hard_stop_reason: str | None = Field(
        default=None,
        description="Computed in Python from the draft's grounded facts, never written by the model.",
    )
    verdict: str | None = None
    cv_tailoring: CvTailoring | None = Field(
        default=None, description="Null when a hard stop fired, otherwise always present."
    )
    cover_letter: CoverLetter | None = Field(
        default=None, description="Null when a hard stop fired, otherwise always present."
    )


class Contact(StageOutput):
    """One person worth reaching out to."""

    contact_name: str = Field(description="The person's name, as their profile gives it.")
    contact_title: str | None = Field(default=None, description="Their role at the company.")
    contact_type: ContactType | None = Field(
        default=None, description="How they relate to this application."
    )
    contact_linkedin: str = Field(
        description="Their profile URL, copied exactly from the candidate list you were given."
    )
    fit_score: float = Field(
        description=(
            "1 to 5: how closely this specific person's role and visible background "
            "match the actual job description you were given -- not just whether their "
            "title sounds relevant, but whether their team, seniority and focus line up "
            "with what the posting actually asks for."
        )
    )
    fit_reason: str = Field(
        description="One short sentence grounding the fit_score in this person's actual profile."
    )
    message: str = Field(description="Outreach draft, 300 characters or fewer.")


class SearchQueries(StageOutput):
    """Search phrasings proposed for find_contact, before any search runs.

    The model never calls a tool or sees a result: it only writes these
    strings, and find_contact.py is what actually queries the web with them.
    That keeps fabrication impossible regardless of how creative the phrasing
    gets -- the final contact is still checked against the URLs a real search
    actually returned, not against anything claimed here.
    """

    queries: list[str] = Field(
        default_factory=list,
        description=(
            "3 to 5 search-engine queries most likely to surface a LinkedIn profile "
            "for this outreach. No search operators (no site:, no quotes) -- the "
            "backend is not Google and returns nothing for them."
        ),
    )


class Shortlist(StageOutput):
    """What find_contact returns: the people worth writing to, best first."""

    contacts: list[Contact] = Field(
        default_factory=list, description="Up to three targets, most worth contacting first."
    )
    reason: str | None = Field(
        default=None, description="Why the shortlist is empty. Null when it is not."
    )

    def grounded_in(self, urls: set[str]) -> "Shortlist":
        """Drop anyone unverifiable, then rank and cap by fit to the JD.

        The searching happens in Python, so the set of real people is known
        exactly: anyone outside it was invented, whatever the prompt said.
        The cap at three and the ordering by fit_score are enforced here too,
        rather than trusted from the model's own list order -- the same
        reasoning as the URL check: a number Python can verify beats one it
        has to take the model's word for.

        Args:
            urls: The profile URLs this stage looked up.

        Returns:
            The shortlist, with unverifiable people removed and the rest
            sorted best-fit-first, capped at three.
        """
        self.contacts = [c for c in self.contacts if c.contact_linkedin in urls]
        self.contacts.sort(key=lambda c: c.fit_score, reverse=True)
        self.contacts = self.contacts[:3]
        if not self.contacts and not self.reason:
            self.reason = "the shortlist named nobody from the profiles found"
        return self
