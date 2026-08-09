from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_artifacts_exige_un_tag_annote_et_verifie() -> None:
    script = (ROOT / "deployment/scripts/vps/release-artifacts.sh").read_text()

    assert '"${TAG}^{tag}"' in script
    assert 'git verify-tag "${TAG}"' in script
    assert '"${OUTPUT_DIR}/tag-verification.txt"' in script
    assert "git tag -s ${TAG} <sha-candidat>" in script
    assert "git tag -s ${TAG} -f" not in script


def test_procedure_signe_et_verifie_le_tag_avant_les_artefacts() -> None:
    procedure = (ROOT / "docs/validation/procedure_fermeture_mvp_1_0.md").read_text()

    release_block = procedure.split("export RELEASE_SIGNING_KEY", maxsplit=1)[1]
    tag_position = release_block.index('git tag -s v1.0.0-mvp "${CANDIDATE_SHA}"')
    verification_position = release_block.index("git verify-tag v1.0.0-mvp")
    artifacts_position = release_block.index(
        "deployment/scripts/vps/release-artifacts.sh v1.0.0-mvp"
    )
    push_position = release_block.index("git push origin v1.0.0-mvp")

    assert tag_position < verification_position < artifacts_position < push_position
