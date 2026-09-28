"""Aliasing surfaces a technology's other spelling; it never invents one."""

from services.asyncapply.utils.documents.aliases import apply_aliases


def test_a_matching_alias_is_appended():
    result = apply_aliases(["Go"], "We need a Golang engineer.")
    assert result == ["Go (Golang)"]


def test_no_alias_present_in_the_jd_leaves_the_entry_alone():
    result = apply_aliases(["Go"], "We need a backend engineer.")
    assert result == ["Go"]


def test_a_technology_with_no_known_alias_is_untouched():
    result = apply_aliases(["Rust"], "We use Rust and Golang here.")
    assert result == ["Rust"]


def test_the_profiles_own_spelling_is_never_flagged_as_its_own_alias():
    """The JD using the same spelling the profile already has is not a gap."""
    result = apply_aliases(["Golang"], "We need a Golang engineer.")
    assert result == ["Golang"]


def test_word_boundaries_are_respected():
    """'js' must not match inside 'objects' or similar."""
    result = apply_aliases(["JavaScript"], "We work with objects and services.")
    assert result == ["JavaScript"]


def test_nothing_is_added_or_removed_from_the_list():
    result = apply_aliases(["Go", "Python", "Rust"], "Golang and Python required.")
    assert len(result) == 3
    assert result[1] == "Python"
    assert result[2] == "Rust"


def test_empty_jd_text_is_a_no_op():
    assert apply_aliases(["Go", "Kubernetes"], "") == ["Go", "Kubernetes"]


def test_a_three_way_group_picks_whichever_alias_is_present():
    result = apply_aliases(["CI/CD"], "Experience with Continuous Deployment pipelines.")
    assert result == ["CI/CD (Continuous Deployment)"]
