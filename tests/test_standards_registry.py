from __future__ import annotations

from datetime import date

import pytest

from hydro_shared.standards_registry import (
    StandardEditionReference,
    bind_ruleset_to_standard,
    binding_matches_standard,
)


def _approved_standard(edition: str = "2025") -> StandardEditionReference:
    return StandardEditionReference(
        standard_code="STD-DEMO",
        edition=edition,
        publisher="Publisher",
        source_ref=f"licensed://standards/std-demo/{edition}",
        acquired_for_project=True,
        reviewed_by="engineering-review",
        review_date=date(2026, 8, 10),
    )


def test_ruleset_binding_requires_acquired_and_reviewed_edition() -> None:
    binding = bind_ruleset_to_standard(
        standard=_approved_standard(),
        ruleset_id="RULESET-DEMO",
        ruleset_version="1.2.0",
        implementation_ref="git://PETROLE/rules/demo@abc123",
        approval_ref="review://engineering/42",
    )

    assert binding.standard_code == "STD-DEMO"
    assert binding.standard_edition == "2025"
    assert binding_matches_standard(binding, _approved_standard("2025")) is True
    assert binding_matches_standard(binding, _approved_standard("2026")) is False


def test_unreviewed_standard_cannot_bind_contractual_rules() -> None:
    standard = StandardEditionReference(
        standard_code="STD-DEMO",
        edition="2025",
        publisher="Publisher",
        source_ref="official://catalog/std-demo/2025",
        acquired_for_project=False,
    )
    with pytest.raises(PermissionError, match="acquise légalement et revue"):
        bind_ruleset_to_standard(
            standard=standard,
            ruleset_id="RULESET-DEMO",
            ruleset_version="1.0.0",
            implementation_ref="git://PETROLE/rules/demo@abc123",
            approval_ref="review://pending",
        )


def test_review_metadata_must_be_complete() -> None:
    with pytest.raises(ValueError, match="renseignés ensemble"):
        StandardEditionReference(
            standard_code="STD-DEMO",
            edition="2025",
            publisher="Publisher",
            source_ref="licensed://standards/std-demo/2025",
            acquired_for_project=True,
            reviewed_by="engineering-review",
        )
