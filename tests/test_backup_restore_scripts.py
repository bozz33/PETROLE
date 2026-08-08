from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_verification_restaure_la_sauvegarde_dans_postgresql_jetable() -> None:
    script = (ROOT / "deployment/scripts/vps/verify-backup-restore.sh").read_text()

    assert "docker run --detach --rm" in script
    assert "pg_restore" in script
    assert "--no-owner --no-privileges" in script
    assert "tar -xzf" in script
    assert "restored_in_isolated_container" in script
    assert "docker rm --force" in script


def test_qualification_execute_une_sauvegarde_et_sa_restauration() -> None:
    script = (ROOT / "deployment/scripts/vps/qualify.sh").read_text()

    assert 'backup.sh" "${mode}" "${fichier_env}"' in script
    assert 'verify-backup-restore.sh"' in script
    assert '"${preuves}/backup-restore.json"' in script


def test_timer_de_sauvegarde_est_quotidien_et_persistant() -> None:
    timer = (ROOT / "deployment/systemd/petrole-backup.timer").read_text()
    service = (ROOT / "deployment/systemd/petrole-backup.service").read_text()

    assert "OnCalendar=*-*-* 00:15:00" in timer
    assert "Persistent=true" in timer
    assert "backup.sh production" in service
