"""Tests for services.asyncapply.profile_schema: the structured Profile must
round-trip through the same dict shape load_context() and the CV renderers
(html.py, fit.py) already expect."""

from services.asyncapply.profile_schema import (
    CvEntry,
    Profile,
    ProfileCandidate,
    ProfileCv,
    ProfileTargeting,
    profile_from_dict,
    profile_to_dict,
)


def test_a_full_profile_round_trips_through_dict_and_back():
    original = Profile(
        candidate=ProfileCandidate(full_name="Ada Lovelace", location="London, UK", email="ada@example.com"),
        custom_house_rules="No crypto companies.",
        location=ProfileTargeting(authorized_in=["GB", "EU"], work_auth_note="Visa ready"),
        target_roles=["Backend Engineer"],
        cv=ProfileCv(
            summary="A pioneer.",
            technologies=["Python", "SQL"],
            education=[CvEntry(heading="Cambridge", subheading="Mathematics", dates="1840")],
            experience=[CvEntry(heading="Analytical Engine Project", bullets=["Wrote the first algorithm."])],
            awards=[CvEntry(heading="Countess of Lovelace", text="Honorary title.")],
        ),
    )

    data = profile_to_dict(original)
    restored = profile_from_dict(data)

    assert restored.candidate.full_name == "Ada Lovelace"
    assert restored.location.authorized_in == ["GB", "EU"]
    assert restored.location.work_auth_note == "Visa ready"
    assert restored.cv.education[0].subheading == "Mathematics"
    assert restored.cv.awards[0].text == "Honorary title."


def test_work_permits_line_is_derived_not_asked():
    """No sponsorship checkbox: outside authorized_in, sponsorship is
    definitionally needed, so the line states it without asking twice."""
    profile = Profile(
        candidate=ProfileCandidate(full_name="Ada"),
        location=ProfileTargeting(authorized_in=["ES", "EU"], work_auth_note="Via IE University"),
    )
    data = profile_to_dict(profile)
    assert data["cv"]["work_permits"] == "Work authorization: ES, EU (sponsorship needed elsewhere) | Via IE University"


def test_an_empty_profile_still_produces_the_keys_downstream_code_reads():
    """html.py/fit.py call cv.get('education', []) etc unconditionally --
    every section must exist, even empty, not be missing entirely."""
    data = profile_to_dict(Profile(candidate=ProfileCandidate(full_name="")))
    for section in ("education", "experience", "projects", "awards", "activities", "technologies"):
        assert data["cv"][section] == []


def test_profile_from_dict_defaults_a_missing_profile_to_an_empty_shell():
    profile = profile_from_dict({})
    assert profile.candidate.full_name == ""
    assert profile.cv.education == []
    assert profile.location.authorized_in == []
