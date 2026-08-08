#!/usr/bin/env bash
# Installe le timer systemd de sauvegarde PETROLE sur un VPS Linux.

set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Ce script doit être exécuté en root pour installer le timer systemd." >&2
    exit 2
fi

racine="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
for fichier in petrole-backup.service petrole-backup.timer; do
    source="${racine}/deployment/systemd/${fichier}"
    destination="/etc/systemd/system/${fichier}"
    if [[ ! -f "${source}" ]]; then
        echo "Unité systemd introuvable : ${source}." >&2
        exit 2
    fi
    install -m 0644 "${source}" "${destination}"
done

systemctl daemon-reload
systemctl enable --now petrole-backup.timer
systemctl status --no-pager petrole-backup.timer
