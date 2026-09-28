"""Builds the candidate's context from their DB row, and reads the stage prompts."""

from dataclasses import dataclass
from pathlib import Path

import yaml

CONTEXT_DIR = Path(__file__).parent
MODES_DIR = CONTEXT_DIR / "modes"
TEMPLATES_DIR = CONTEXT_DIR / "templates"
EXAMPLE_PROFILE_PATH = CONTEXT_DIR / "user" / "profile.example.yml"


@dataclass
class AsyncApplyContext:
    """One user's personal context, loaded once per batch.

    profile is the single source of truth: identity, targeting rules and the
    whole CV (the fixed sections plus the roles and projects the model
    tailors). It comes from users.profile_yaml -- per-user, in the DB -- not
    a shared file on disk, since a single deployment now serves many people.
    """

    profile: dict
    agent_dna: str


def load_context(profile_yaml: str | None, agent_dna_md: str | None = "") -> AsyncApplyContext:
    """Build a user's context from their stored profile and agent DNA.

    Args:
        profile_yaml: The user's profile.yml content, as stored on their row.
        agent_dna_md: The user's agent DNA (writing-voice preferences), or "".

    Returns:
        The parsed personal context.

    Raises:
        ValueError: if profile_yaml is empty or does not parse to a mapping --
            nothing can be evaluated without it.
    """
    if not profile_yaml or not profile_yaml.strip():
        raise ValueError("profile is empty -- complete your profile before submitting a batch")

    parsed = yaml.safe_load(profile_yaml)
    if not isinstance(parsed, dict):
        raise ValueError("profile does not parse to a YAML mapping")

    return AsyncApplyContext(profile=parsed, agent_dna=agent_dna_md or "")


def load_mode(name: str) -> str:
    """Read one stage prompt from context/modes.

    Args:
        name: File stem, e.g. "evaluate_job" for modes/evaluate_job.md.

    Returns:
        The mode's markdown content.
    """
    return (MODES_DIR / f"{name}.md").read_text()
