"""Builds the candidate's context from their DB row, and reads the stage prompts."""

from dataclasses import dataclass
from pathlib import Path

CONTEXT_DIR = Path(__file__).parent
MODES_DIR = CONTEXT_DIR / "modes"
TEMPLATES_DIR = CONTEXT_DIR / "templates"
EXAMPLE_PROFILE_PATH = CONTEXT_DIR / "user" / "profile.example.yml"


@dataclass
class AsyncApplyContext:
    """One user's personal context, loaded once per batch.

    profile is the single source of truth: identity, targeting rules and the
    whole CV (the fixed sections plus the roles and projects the model
    tailors). It comes from users.profile -- per-user, in the DB -- not
    a shared file on disk, since a single deployment now serves many people.
    """

    profile: dict
    agent_dna: str


def load_context(profile: dict | None, agent_dna_md: str | None = "") -> AsyncApplyContext:
    """Build a user's context from their stored profile and agent DNA.

    Args:
        profile: The user's profile, as stored on their row (users.profile).
        agent_dna_md: The user's agent DNA (writing-voice preferences), or "".

    Returns:
        The parsed personal context.

    Raises:
        ValueError: if profile is empty or not a mapping -- nothing can be
            evaluated without it.
    """
    if not profile or not isinstance(profile, dict):
        raise ValueError("profile is empty -- complete your profile before submitting a batch")

    return AsyncApplyContext(profile=profile, agent_dna=agent_dna_md or "")


def load_mode(name: str) -> str:
    """Read one stage prompt from context/modes.

    Args:
        name: File stem, e.g. "evaluate_job" for modes/evaluate_job.md.

    Returns:
        The mode's markdown content.
    """
    return (MODES_DIR / f"{name}.md").read_text()
