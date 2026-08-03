#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
readonly REPOSITORY_ROOT
readonly TEMPLATE="${REPOSITORY_ROOT}/deployment/.env.vps.example"
readonly DESTINATION="${REPOSITORY_ROOT}/deployment/.env.vps"

domaine="${1:-}"
adresse_courriel="${2:-}"
if [[ -z "${domaine}" || -z "${adresse_courriel}" ]]; then
    echo "Usage : $0 domaine.example administrateur@example.com" >&2
    exit 2
fi
if [[ ! "${domaine}" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$ || "${domaine}" == *..* ]]; then
    echo "Le nom de domaine est invalide : ${domaine}" >&2
    exit 2
fi
if [[ ! "${adresse_courriel}" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
    echo "L'adresse de contact ACME est invalide." >&2
    exit 2
fi
if [[ -e "${DESTINATION}" ]]; then
    echo "Le fichier ${DESTINATION} existe déjà ; aucun écrasement effectué." >&2
    exit 2
fi

secret_jwt="$(openssl rand -hex 48)"
secret_postgres="$(openssl rand -hex 32)"
secret_minio="$(openssl rand -hex 32)"

sed \
    -e "s|staging.exemple.com|${domaine}|" \
    -e "s|administrateur@exemple.com|${adresse_courriel}|" \
    -e "s|CHANGE_ME_64_CARACTERES_ALEATOIRES|${secret_jwt}|" \
    -e "s|CHANGE_ME_MOT_DE_PASSE_POSTGRES|${secret_postgres}|" \
    -e "s|CHANGE_ME_MOT_DE_PASSE_MINIO|${secret_minio}|" \
    "${TEMPLATE}" >"${DESTINATION}"
chmod 600 "${DESTINATION}"

echo "Configuration créée : ${DESTINATION}"
echo "Conservez une copie chiffrée ; ce fichier ne doit jamais être ajouté à Git."
