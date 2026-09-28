"""The structured shape of a user's profile: what the form collects, what a
CV upload can best-effort fill in, and how the two turn into the YAML text
load_context() actually reads.

This schema is deliberately the single source of truth in three places at
once: the request/response body for the profile form endpoints, the
schema-constrained output of the CV-extraction call, and the shape
serialized to YAML for storage. Keeping one definition means the form, the
AI fill, and the pipeline's own reader can never quietly drift apart.
"""

from pydantic import BaseModel, ConfigDict, Field


class CvEntry(BaseModel):
    """One block in a CV section: a job, a degree, a project, or a one-line award.

    A block entry (job/degree/project) uses heading/location/subheading/dates/
    bullets; a one-liner (an award) uses heading/text instead. Both shapes
    coexist in the same list, matching how html.py already renders them.
    """

    model_config = ConfigDict(extra="forbid")

    heading: str = Field(description="The entry's title -- a company, a school, a project name.")
    location: str | None = Field(default=None, description="City, country. Omit if not applicable.")
    subheading: str | None = Field(default=None, description="Role title or degree name.")
    dates: str | None = Field(default=None, description="e.g. 'Summer 2026' or 'Sept 2023 - Present'.")
    bullets: list[str] = Field(default_factory=list, description="Achievement bullets, verbatim.")
    text: str | None = Field(
        default=None, description="For a one-line entry (an award) instead of a bulleted block."
    )


class ProfileCandidate(BaseModel):
    """Contact identity, printed at the top of the CV."""

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(description="As it should appear on the CV.")
    location: str | None = Field(default=None, description="The candidate's own city, e.g. 'Madrid, Spain'.")
    phone: str | None = None
    email: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio_url: str | None = None


class ProfileTargeting(BaseModel):
    """Job-search rules a CV never states outright -- only the candidate knows these."""

    model_config = ConfigDict(extra="forbid")

    authorized_in: list[str] = Field(
        default_factory=list,
        description="Country codes the candidate can legally work in without sponsorship, e.g. ['ES', 'EU'].",
    )
    needs_sponsorship: bool = Field(
        default=False, description="Whether roles outside authorized_in would need visa sponsorship."
    )
    work_auth_note: str | None = Field(
        default=None,
        description="Anything else worth stating on the CV, e.g. 'Eligible to sign an internship "
        "agreement via IE University'. Appended after the auto-generated authorization line.",
    )


class ProfileCv(BaseModel):
    """The fixed CV content: what a model reorders and rewords, never invents."""

    model_config = ConfigDict(extra="forbid")

    summary: str | None = Field(default=None, description="One or two sentences, used only in outreach.")
    languages: str | None = Field(default=None, description="e.g. 'Spanish (Native). English (Fluent).'")
    technologies: list[str] = Field(default_factory=list)
    education: list[CvEntry] = Field(default_factory=list)
    experience: list[CvEntry] = Field(default_factory=list)
    projects: list[CvEntry] = Field(default_factory=list)
    awards: list[CvEntry] = Field(default_factory=list)
    activities: list[CvEntry] = Field(default_factory=list)


class Profile(BaseModel):
    """The full profile: everything the form collects and the pipeline reads."""

    model_config = ConfigDict(extra="forbid")

    candidate: ProfileCandidate
    custom_house_rules: str | None = Field(
        default=None, description="Free-text rules that disqualify a job outright, e.g. 'No crypto.'"
    )
    location: ProfileTargeting = Field(default_factory=ProfileTargeting)
    target_roles: list[str] = Field(default_factory=list)
    cv: ProfileCv = Field(default_factory=ProfileCv)


class ExtractedProfile(BaseModel):
    """What a CV upload can plausibly fill in -- the AI-fillable subset of Profile.

    Everything here is either literally printed on a CV (identity, education,
    experience, projects, awards, activities, technologies) or a light,
    low-risk inference from it (a one-line summary). Job-search targeting
    (authorized_in, needs_sponsorship, target_roles, house rules) is not on a
    CV and stays out of this model entirely, so there is no field here the
    model could be tempted to guess at from thin air.
    """

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio_url: str | None = None
    summary: str | None = Field(
        default=None, description="One or two sentences summarizing the candidate, drawn from the CV."
    )
    languages: str | None = None
    technologies: list[str] = Field(default_factory=list)
    education: list[CvEntry] = Field(default_factory=list)
    experience: list[CvEntry] = Field(default_factory=list)
    projects: list[CvEntry] = Field(default_factory=list)
    awards: list[CvEntry] = Field(default_factory=list)
    activities: list[CvEntry] = Field(default_factory=list)


def _entry_dict(entry: CvEntry) -> dict:
    """Drop an entry's null/empty fields so the stored YAML stays readable.

    Args:
        entry: One CV block.

    Returns:
        Its fields, omitting anything not set.
    """
    return {k: v for k, v in entry.model_dump().items() if v not in (None, "", [])}


def _work_permits_line(targeting: ProfileTargeting) -> str:
    """Build the CV's one-line work-authorization statement from the targeting answers.

    Asked once, as a job-search question, and reused here rather than asked a
    second time as CV copy -- the two are the same fact.

    Args:
        targeting: The candidate's authorization answers.

    Returns:
        A line like "Work authorization: ES, EU | No sponsorship required",
        with work_auth_note appended if given.
    """
    countries = ", ".join(targeting.authorized_in) or "not specified"
    sponsorship = "Sponsorship may be required" if targeting.needs_sponsorship else "No sponsorship required"
    line = f"Work authorization: {countries} | {sponsorship}"
    if targeting.work_auth_note:
        line += f" | {targeting.work_auth_note}"
    return line


def profile_to_dict(profile: Profile) -> dict:
    """Turn a structured Profile into the plain dict load_context() expects.

    This is the one place the two shapes are reconciled: the same keys
    html.py, fit.py and find_contact.py already read from profile.yml.

    Args:
        profile: The validated, structured profile.

    Returns:
        A plain dict, ready for yaml.safe_dump or direct use.
    """
    data: dict = {
        "candidate": {k: v for k, v in profile.candidate.model_dump().items() if v not in (None, "")},
        "location": {
            "authorized_in": profile.location.authorized_in,
            "needs_sponsorship": profile.location.needs_sponsorship,
        },
        "target_roles": profile.target_roles,
        "cv": {
            "work_permits": _work_permits_line(profile.location),
            "languages": profile.cv.languages or "",
            "technologies": profile.cv.technologies,
            "education": [_entry_dict(e) for e in profile.cv.education],
            "experience": [_entry_dict(e) for e in profile.cv.experience],
            "projects": [_entry_dict(e) for e in profile.cv.projects],
            "awards": [_entry_dict(e) for e in profile.cv.awards],
            "activities": [_entry_dict(e) for e in profile.cv.activities],
        },
    }
    if profile.cv.summary:
        data["cv"]["summary"] = profile.cv.summary
    if profile.custom_house_rules:
        data["custom_house_rules"] = profile.custom_house_rules
    return data


def profile_from_dict(data: dict) -> Profile:
    """Parse a stored profile dict back into the structured form the UI edits.

    Args:
        data: The dict parsed from profile.yml (or {} if there isn't one yet).

    Returns:
        A Profile, defaulting every missing piece rather than raising -- an
        incomplete profile is still something the form should be able to
        open and keep filling in.
    """
    candidate = data.get("candidate") or {}
    location = data.get("location") or {}
    cv = data.get("cv") or {}
    return Profile(
        candidate=ProfileCandidate(full_name=candidate.get("full_name") or "", **{
            k: v for k, v in candidate.items() if k != "full_name"
        }),
        custom_house_rules=data.get("custom_house_rules"),
        location=ProfileTargeting(
            authorized_in=location.get("authorized_in") or [],
            needs_sponsorship=bool(location.get("needs_sponsorship", False)),
        ),
        target_roles=data.get("target_roles") or [],
        cv=ProfileCv(
            summary=cv.get("summary"),
            languages=cv.get("languages"),
            technologies=cv.get("technologies") or [],
            education=[CvEntry(**e) for e in cv.get("education") or []],
            experience=[CvEntry(**e) for e in cv.get("experience") or []],
            projects=[CvEntry(**e) for e in cv.get("projects") or []],
            awards=[CvEntry(**e) for e in cv.get("awards") or []],
            activities=[CvEntry(**e) for e in cv.get("activities") or []],
        ),
    )
