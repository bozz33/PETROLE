#!/usr/bin/env bash

set -Eeuo pipefail

# shellcheck source=common.sh
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

mode="${1:-development}"
fichier_env="${2:-${VPS_REPOSITORY_ROOT}/deployment/.env.vps}"
initialiser_contexte_vps "${mode}" "${fichier_env}"

for commande in docker curl git realpath; do
    exiger_commande "${commande}"
done

if grep -Eq 'CHANGE_ME|exemple\.com' "${VPS_ENV_FILE}"; then
    echo "Le fichier d'environnement contient encore une valeur d'exemple." >&2
    exit 2
fi

permissions="$(stat -c '%a' "${VPS_ENV_FILE}")"
if (( 10#${permissions} % 100 != 0 )); then
    echo "Les secrets sont lisibles par le groupe ou les autres utilisateurs (${permissions})." >&2
    echo "Exécutez : chmod 600 ${VPS_ENV_FILE}" >&2
    exit 2
fi

secret_jwt="$(valeur_environnement HYDRO_JWT_SECRET)"
if (( ${#secret_jwt} < 64 )); then
    echo "HYDRO_JWT_SECRET doit contenir au moins 64 caractères sur le VPS." >&2
    exit 2
fi

cd "${VPS_REPOSITORY_ROOT}"
export HYDRO_BUILD_GIT_SHA="$(git rev-parse HEAD)"
export HYDRO_BUILD_REF="$(git symbolic-ref --quiet --short HEAD || git describe --tags --always)"
export HYDRO_BUILD_DATE="$(date --utc --iso-8601=seconds)"

# Les valeurs exportées priment sur le fichier .env du VPS : chaque image
# construite par ce script publie ainsi l'identité exacte du candidat déployé
# via /api/v1/version. Sans ce scellement, une qualification ne pourrait pas
# prouver quel commit a réellement été servi.
compose_vps config --quiet
compose_vps pull --ignore-buildable postgres minio caddy
compose_vps build api worker web
compose_vps up --detach postgres minio
attendre_postgresql
compose_vps run --rm --no-deps api alembic upgrade head
compose_vps up --detach --remove-orphans
attendre_api_locale

domaine="$(valeur_environnement HYDRO_DOMAIN)"
mkdir -p "${VPS_REPOSITORY_ROOT}/var/vps"
jq -n \
    --arg date "$(date --utc --iso-8601=seconds)" \
    --arg commit "$(git rev-parse HEAD)" \
    --arg mode "${VPS_MODE}" \
    --arg domaine "${domaine}" \
    '{deployed_at_utc:$date, commit:$commit, mode:$mode, domain:$domaine, status:"ready"}' \
    >"${VPS_REPOSITORY_ROOT}/var/vps/deployment-state.json"

compose_vps ps
echo "Déploiement prêt. Contrôle public : https://${domaine}/api/v1/health/ready"
