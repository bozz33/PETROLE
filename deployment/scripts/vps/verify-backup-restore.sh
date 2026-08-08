#!/usr/bin/env bash
# Vérifie une sauvegarde PETROLE par restauration complète hors production.
# La base restaurée vit dans un conteneur PostgreSQL jetable, sans port publié.

set -Eeuo pipefail
umask 077

# shellcheck source=common.sh
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ $# -lt 1 || $# -gt 4 ]]; then
    echo "Usage : $0 REPERTOIRE_SAUVEGARDE [development|production] [FICHIER_ENV] [RAPPORT_JSON]" >&2
    exit 2
fi

repertoire_sauvegarde="$1"
mode="${2:-development}"
fichier_env="${3:-${VPS_REPOSITORY_ROOT}/deployment/.env.vps}"
rapport_json="${4:-${repertoire_sauvegarde}/restore-verification.json}"

if [[ ! -d "${repertoire_sauvegarde}" ]]; then
    echo "Le répertoire de sauvegarde est absent : ${repertoire_sauvegarde}." >&2
    exit 2
fi
repertoire_sauvegarde="$(realpath "${repertoire_sauvegarde}")"
rapport_json="$(realpath --canonicalize-missing "${rapport_json}")"
initialiser_contexte_vps "${mode}" "${fichier_env}"

for commande in docker jq sha256sum tar realpath mktemp; do
    exiger_commande "${commande}"
done

manifeste="${repertoire_sauvegarde}/manifest.json"
if [[ ! -f "${manifeste}" || "$(jq -r '.format_version' "${manifeste}")" != "1" ]]; then
    echo "Le manifeste de sauvegarde est absent ou incompatible." >&2
    exit 2
fi

for nom in postgres.dump object-storage.tar.gz; do
    fichier="${repertoire_sauvegarde}/${nom}"
    attendu="$(jq -r --arg nom "${nom}" '.files[] | select(.name==$nom) | .sha256' "${manifeste}")"
    if [[ ! -f "${fichier}" || -z "${attendu}" ]]; then
        echo "L'archive ${nom} est absente ou son empreinte est invalide." >&2
        exit 1
    fi
    actuel="$(sha256sum "${fichier}" | awk '{print $1}')"
    if [[ "${actuel}" != "${attendu}" ]]; then
        echo "L'archive ${nom} est absente ou son empreinte est invalide." >&2
        exit 1
    fi
done

conteneur_source="$(compose_vps ps --quiet postgres)"
if [[ -z "${conteneur_source}" ]]; then
    echo "PostgreSQL PETROLE doit être démarré pour identifier son image de restauration." >&2
    exit 1
fi
image_postgres="$(docker inspect --format '{{.Config.Image}}' "${conteneur_source}")"
nom_temporaire="petrole-backup-verify-$-$RANDOM"
mot_de_passe_temporaire="verification-$RANDOM-$RANDOM"
base_temporaire="petrole_restore_verification"
utilisateur_temporaire="petrole_restore_verification"
repertoire_objets="$(mktemp -d "${TMPDIR:-/tmp}/petrole-object-restore.XXXXXX")"
debut="$(date +%s)"

nettoyer() {
    docker rm --force "${nom_temporaire}" >/dev/null 2>&1 || true
    rm -rf "${repertoire_objets}"
}
trap nettoyer EXIT

# Refuse toute archive qui tenterait de sortir de son répertoire jetable.
if tar -tzf "${repertoire_sauvegarde}/object-storage.tar.gz" | \
    awk 'BEGIN { valide=1 } /^\// || /(^|\/)\.\.($|\/)/ { valide=0 } END { exit !valide }'; then
    :
else
    echo "L'archive du stockage objet contient un chemin non sûr." >&2
    exit 1
fi
tar -xzf "${repertoire_sauvegarde}/object-storage.tar.gz" -C "${repertoire_objets}"
nombre_objets="$(find "${repertoire_objets}" -type f | wc -l | tr -d ' ')"

docker run --detach --rm --name "${nom_temporaire}" \
    -e "POSTGRES_DB=${base_temporaire}" \
    -e "POSTGRES_USER=${utilisateur_temporaire}" \
    -e "POSTGRES_PASSWORD=${mot_de_passe_temporaire}" \
    "${image_postgres}" >/dev/null

for tentative in $(seq 1 60); do
    # L'image PostGIS accepte brièvement des connexions pendant son init, puis
    # redémarre PostgreSQL avant de lancer le processus définitif. Attendre la
    # fin explicite de l'init évite d'interrompre pg_restore à ce redémarrage.
    if docker logs "${nom_temporaire}" 2>&1 | grep -q \
        'PostgreSQL init process complete; ready for start up.' \
        && docker exec "${nom_temporaire}" pg_isready \
            -U "${utilisateur_temporaire}" -d "${base_temporaire}" >/dev/null 2>&1; then
        break
    fi
    if [[ "${tentative}" -eq 60 ]]; then
        echo "PostgreSQL jetable n'est pas prêt après 120 secondes." >&2
        exit 1
    fi
    sleep 2
done

docker cp "${repertoire_sauvegarde}/postgres.dump" "${nom_temporaire}:/tmp/petrole-backup.dump"
docker exec "${nom_temporaire}" pg_restore --list /tmp/petrole-backup.dump >/dev/null
# L'initialisation de l'image PostGIS ajoute des extensions au nom de base
# fourni. Recréer la cible depuis template0 permet de vérifier la création des
# extensions et de tous les schémas exactement comme lors d'une restauration.
docker exec "${nom_temporaire}" dropdb \
    -U "${utilisateur_temporaire}" --if-exists "${base_temporaire}"
docker exec "${nom_temporaire}" createdb \
    -U "${utilisateur_temporaire}" -T template0 "${base_temporaire}"
docker exec "${nom_temporaire}" pg_restore \
    -U "${utilisateur_temporaire}" -d "${base_temporaire}" \
    --no-owner --no-privileges /tmp/petrole-backup.dump

nombre_tables="$(docker exec "${nom_temporaire}" psql \
    -U "${utilisateur_temporaire}" -d "${base_temporaire}" -Atc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")"
revision_restauree="$(docker exec "${nom_temporaire}" psql \
    -U "${utilisateur_temporaire}" -d "${base_temporaire}" -Atc \
    'SELECT version_num FROM alembic_version LIMIT 1;')"
if [[ ! "${nombre_tables}" =~ ^[1-9][0-9]*$ || -z "${revision_restauree}" ]]; then
    echo "La restauration jetable ne contient pas le schéma PETROLE attendu." >&2
    exit 1
fi

duree="$(( $(date +%s) - debut ))"
mkdir -p "$(dirname "${rapport_json}")"
jq -n \
    --arg date "$(date --utc --iso-8601=seconds)" \
    --arg source "${repertoire_sauvegarde}" \
    --arg image "${image_postgres}" \
    --arg revision_source "$(jq -r '.alembic_revision' "${manifeste}")" \
    --arg revision_restauree "${revision_restauree}" \
    --argjson tables "${nombre_tables}" \
    --argjson objects "${nombre_objets}" \
    --argjson duration_s "${duree}" \
    '{
      verified_at_utc:$date,
      source_backup:$source,
      postgres_image:$image,
      source_alembic_revision:$revision_source,
      restored_alembic_revision:$revision_restauree,
      restored_public_table_count:$tables,
      restored_object_count:$objects,
      duration_s:$duration_s,
      status:"restored_in_isolated_container"
    }' >"${rapport_json}"

echo "${rapport_json}"
