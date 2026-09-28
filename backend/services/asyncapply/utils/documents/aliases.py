"""Surfaces a technology's alternate spelling when the posting uses a
different one than the profile does.

Reordering the technologies list (done in evaluate_job) is not enough on its
own: a naive ATS does literal string matching, so a profile that says "Go"
scores zero against a posting that says "Golang" even though they are the
same skill. This never invents a technology the profile does not list -- it
only ever appends a second spelling of one that is already there, and only
when the posting's own text actually uses it.
"""

import re

# Each set is one skill's known spellings. Deliberately short: covering the
# handful of common splits (not a general synonym dictionary) keeps this
# reviewable and keeps every entry an actual literal-matching gap, not a
# guess at what an ATS might consider related.
ALIAS_GROUPS = [
    {"Go", "Golang"},
    {"Kubernetes", "K8s"},
    {"JavaScript", "JS"},
    {"TypeScript", "TS"},
    {"PostgreSQL", "Postgres"},
    {"MongoDB", "Mongo"},
    {"CI/CD", "Continuous Integration", "Continuous Deployment"},
]

_GROUP_BY_LOWER = {alias.lower(): group for group in ALIAS_GROUPS for alias in group}


def _mentions(term: str, text: str) -> bool:
    """Whether `term` appears in `text` as a whole word, case-insensitive."""
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE) is not None


def apply_aliases(technologies: list[str], jd_text: str) -> list[str]:
    """Append the posting's own spelling next to a technology that has one.

    Args:
        technologies: The profile's technology entries, already chosen and
            ordered by evaluate_job. Never added to or removed from -- only
            reworded in place.
        jd_text: The posting text, checked for which spelling it actually uses.

    Returns:
        The same entries, with " (Alias)" appended where the posting uses a
        different spelling of a technology already on the list.
    """
    if not jd_text:
        return technologies

    result = []
    for tech in technologies:
        group = _GROUP_BY_LOWER.get(tech.lower())
        if not group:
            result.append(tech)
            continue

        match = next(
            (alias for alias in group if alias.lower() != tech.lower() and _mentions(alias, jd_text)),
            None,
        )
        result.append(f"{tech} ({match})" if match else tech)
    return result
