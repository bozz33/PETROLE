#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

# shellcheck source=common.sh
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

mode="${1:-development}"
fichier_env="${2:-${VPS_REPOSITORY_ROOT}/deployment/.env.vps}"
repertoire_parent="${3:-${VPS_REPOSITORY_ROOT}/var/backups-vps}"
initialiser_contexte_vps "${mode}" "${fichier_env}"

for commande in docker jq sha256sum realpath; do
    exiger_commande "${commande}"
done

horodatage="$(date --utc +%Y%m%dT%H%M%SZ)"
destination="$(realpath --canonicalize-missing "${repertoire_parent}")/${horodatage}"
mkdir -p "${destination}"

conteneur_postgres="$(compose_vps ps --quiet postgres)"
conteneur_minio="$(compose_vps ps --quiet minio)"
if [[ -z "${conteneur_postgres}" || -z "${conteneur_minio}" ]]; then
    echo "PostgreSQL et MinIO doivent être démarrés avant la sauvegarde." >&2
    exit 1
fi

services_a_redemarrer=()
# Le proxy nginx interne résout l'adresse Docker de l'API au démarrage. Il doit
# donc être redémarré avec l'API après un snapshot cohérent, sinon il conserverait
# l'ancienne adresse du conteneur et servirait des 502 jusqu'au prochain restart.
for service in api worker minio web; do
    conteneur="$(compose_vps ps --quiet "${service}")"
    if [[ -n "${conteneur}" ]]; then
        services_a_redemarrer+=("${service}")
    fi
done

redemarrer_services() {
    if (( ${#services_a_redemarrer[@]} > 0 )); then
        compose_vps up --detach "${services_a_redemarrer[@]}" >/dev/null
    fi
}
trap 'redemarrer_services || true' EXIT
compose_vps stop "${services_a_redemarrer[@]}"

archive_postgres="${destination}/postgres.dump"
archive_objets="${destination}/object-storage.tar.gz"

compose_vps exec -T postgres sh -c \
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
    >"${archive_postgres}"
compose_vps exec -T postgres pg_restore --list <"${archive_postgres}" >/dev/null

image_utilitaire="$(docker inspect --format '{{.Config.Image}}' "${conteneur_postgres}")"
docker run --rm \
    --volumes-from "${conteneur_minio}" \
    --mount "type=bind,source=${destination},target=/backup" \
    --entrypoint sh "${image_utilitaire}" \
    -c 'tar -czf /backup/object-storage.tar.gz -C /data . && tar -tzf /backup/object-storage.tar.gz >/dev/null'

revision_alembic="$(compose_vps run --rm --no-deps api alembic current | head -n 1 | tr -d '\r')"
empreinte_postgres="$(sha256sum "${archive_postgres}" | awk '{print $1}')"
empreinte_objets="$(sha256sum "${archive_objets}" | awk '{print $1}')"
taille_postgres="$(stat -c '%s' "${archive_postgres}")"
taille_objets="$(stat -c '%s' "${archive_objets}")"

jq -n \
    --arg date "$(date --utc --iso-8601=seconds)" \
    --arg revision "${revision_alembic}" \
    --arg hash_postgres "${empreinte_postgres}" \
    --arg hash_objets "${empreinte_objets}" \
    --argjson taille_postgres "${taille_postgres}" \
    --argjson taille_objets "${taille_objets}" \
    '{
      format_version:1,
      created_at_utc:$date,
      alembic_revision:$revision,
      files:[
        {name:"postgres.dump",sha256:$hash_postgres,size_bytes:$taille_postgres},
        {name:"object-storage.tar.gz",sha256:$hash_objets,size_bytes:$taille_objets}
      ]
    }' >"${destination}/manifest.json"

redemarrer_services
trap - EXIT

echo "${destination}"
