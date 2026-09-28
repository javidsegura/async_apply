"""Reads the candidate's context (context/user) and the stage prompts (context/modes)."""

from dataclasses import dataclass
from pathlib import Path

import yaml

CONTEXT_DIR = Path(__file__).parent
USER_DIR = CONTEXT_DIR / "user"
MODES_DIR = CONTEXT_DIR / "modes"
TEMPLATES_DIR = CONTEXT_DIR / "templates"


@dataclass
class AsyncApplyContext:
    """The candidate's personal context, loaded once per batch.

    profile.yml is the single source of truth: identity, targeting rules and the
    whole CV (the fixed sections plus the roles and projects the model tailors).
    """

    profile: dict
    voice_dna: str


def load_context() -> AsyncApplyContext:
    """Read profile.yml and voice_dna.md from context/user.

    Returns:
        The parsed personal context.

    Raises:
        FileNotFoundError: if profile.yml is missing, since nothing can be
            evaluated without it.
    """
    profile_path = USER_DIR / "profile.yml"
    if not profile_path.exists():
        raise FileNotFoundError(f"{profile_path} is missing. See services/asyncapply/README.md.")

    voice_path = USER_DIR / "voice_dna.md"
    return AsyncApplyContext(
        profile=yaml.safe_load(profile_path.read_text()),
        voice_dna=voice_path.read_text() if voice_path.exists() else "",
    )


def load_mode(name: str) -> str:
    """Read one stage prompt from context/modes.

    Args:
        name: File stem, e.g. "evaluate_job" for modes/evaluate_job.md.

    Returns:
        The mode's markdown content.
    """
    return (MODES_DIR / f"{name}.md").read_text()
