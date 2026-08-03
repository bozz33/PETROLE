#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

# shellcheck source=common.sh
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ "${1:-}" != "--confirm-replacement" ]]; then
    echo "Usage : $0 --confirm-replacement REPERTOIRE_SAUVEGARDE [development|production] [FICHIER_ENV]" >&2
    exit 2
fi

repertoire_sauvegarde="${2:-}"
mode="${3:-development}"
fichier_env="${4:-${VPS_REPOSITORY_ROOT}/deployment/.env.vps}"
if [[ -z "${repertoire_sauvegarde}" || ! -d "${repertoire_sauvegarde}" ]]; then
    echo "Le répertoire de sauvegarde est absent." >&2
    exit 2
fi
repertoire_sauvegarde="$(realpath "${repertoire_sauvegarde}")"
initialiser_contexte_vps "${mode}" "${fichier_env}"

for commande in docker jq sha256sum realpath; do
    exiger_commande "${commande}"
done

manifeste="${repertoire_sauvegarde}/manifest.json"
if [[ ! -f "${manifeste}" || "$(jq -r '.format_version' "${manifeste}")" != "1" ]]; then
    echo "Le manifeste est absent ou incompatible." >&2
    exit 2
fi

for nom in postgres.dump object-storage.tar.gz; do
    fichier="${repertoire_sauvegarde}/${nom}"
    attendu="$(jq -r --arg nom "${nom}" '.files[] | select(.name==$nom) | .sha256' "${manifeste}")"
    if [[ ! -f "${fichier}" || -z "${attendu}" ]]; then
        echo "Archive requise absente : ${nom}" >&2
        exit 2
    fi
    actuel="$(sha256sum "${fichier}" | awk '{print $1}')"
    if [[ "${actuel}" != "${attendu}" ]]; then
        echo "Empreinte invalide pour ${nom}." >&2
        exit 1
    fi
done

compose_vps up --detach postgres minio
attendre_postgresql
compose_vps stop api worker web minio

conteneur_postgres="$(compose_vps ps --all --quiet postgres)"
conteneur_minio="$(compose_vps ps --all --quiet minio)"
image_utilitaire="$(docker inspect --format '{{.Config.Image}}' "${conteneur_postgres}")"
chemin_temporaire="/tmp/hydro-restore-${RANDOM}.dump"

docker cp "${repertoire_sauvegarde}/postgres.dump" \
    "${conteneur_postgres}:${chemin_temporaire}"
compose_vps exec -T postgres pg_restore --list "${chemin_temporaire}" >/dev/null
docker run --rm \
    --mount "type=bind,source=${repertoire_sauvegarde},target=/backup,readonly" \
    --entrypoint sh "${image_utilitaire}" \
    -c 'tar -tzf /backup/object-storage.tar.gz >/dev/null'

compose_vps exec -T postgres sh -c \
    'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
compose_vps exec -T postgres sh -c \
    "pg_restore -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --no-owner --no-privileges '${chemin_temporaire}'"

docker run --rm \
    --volumes-from "${conteneur_minio}" \
    --mount "type=bind,source=${repertoire_sauvegarde},target=/backup,readonly" \
    --entrypoint sh "${image_utilitaire}" \
    -c 'find /data -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + && tar -xzf /backup/object-storage.tar.gz -C /data'

compose_vps exec -T postgres rm -f "${chemin_temporaire}"
compose_vps run --rm --no-deps api alembic upgrade head
compose_vps up --detach minio api worker web caddy
attendre_api_locale

jq -n \
    --arg date "$(date --utc --iso-8601=seconds)" \
    --arg source "${repertoire_sauvegarde}" \
    --arg revision "$(jq -r '.alembic_revision' "${manifeste}")" \
    '{restored_at_utc:$date,backup_directory:$source,source_alembic_revision:$revision,status:"restored"}' \
    >"${repertoire_sauvegarde}/restore-result.json"

echo "Restauration terminée et API prête."
