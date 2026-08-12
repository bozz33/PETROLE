from __future__ import annotations

import pytest

from hydro_api.industrial.quality_mapping import QualityMappingRegistry, QualityMappingRule


def _registry() -> QualityMappingRegistry:
    return QualityMappingRegistry(
        provider="historian-demo",
        version="quality-map-v2",
        source_ref="vendor-doc://historian-demo/quality/v2",
        rules=(
            QualityMappingRule("192", "good", "vendor-doc://historian-demo/quality/v2#good"),
            QualityMappingRule(
                "64",
                "uncertain",
                "vendor-doc://historian-demo/quality/v2#uncertain",
            ),
            QualityMappingRule("0", "bad", "vendor-doc://historian-demo/quality/v2#bad"),
        ),
    )


def test_quality_mapping_preserves_source_code_and_rule_provenance() -> None:
    result = _registry().map_quality("64")

    assert result.target_quality == "uncertain"
    assert result.source_code == "64"
    assert result.registry_version == "quality-map-v2"
    assert result.rule_source_ref.endswith("#uncertain")


def test_unknown_vendor_quality_has_no_good_fallback() -> None:
    with pytest.raises(KeyError, match="non mappé"):
        _registry().map_quality("255")


def test_quality_registry_refuses_duplicate_source_code() -> None:
    rule = QualityMappingRule("192", "good", "vendor-doc://quality/good")
    with pytest.raises(ValueError, match="qu'une fois"):
        QualityMappingRegistry(
            provider="historian-demo",
            version="v1",
            source_ref="vendor-doc://quality",
            rules=(rule, rule),
        )
