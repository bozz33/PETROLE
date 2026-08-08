#!/usr/bin/env bash
# Ferme les portes techniques du MVP sans prétendre remplacer l'acceptation métier.
#
# Variables obligatoires :
#   RECETTE_ENGINEER_EMAIL
#   RECETTE_ENGINEER_PASSWORD
#   RECETTE_APPROVER_EMAIL
#   RECETTE_APPROVER_PASSWORD
#
# Variables facultatives :
#   PETROLE_BASE_URL        défaut : https://petrole.distesage.com/api/v1
#   PETROLE_PROFILE         défaut : production
#   PREPARE_REFERENCE       1 pour (re)créer REF-MVP-01, 0 sinon
#   SECONDARY_BASE_URL      instance locale/de test servant le même build
#   SECONDARY_EMAIL
#   SECONDARY_PASSWORD

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT_DIR}"

: "${RECETTE_ENGINEER_EMAIL:?RECETTE_ENGINEER_EMAIL est requis}"
: "${RECETTE_ENGINEER_PASSWORD:?RECETTE_ENGINEER_PASSWORD est requis}"
: "${RECETTE_APPROVER_EMAIL:?RECETTE_APPROVER_EMAIL est requis}"
: "${RECETTE_APPROVER_PASSWORD:?RECETTE_APPROVER_PASSWORD est requis}"

BASE_URL="${PETROLE_BASE_URL:-https://petrole.distesage.com/api/v1}"
PROFILE="${PETROLE_PROFILE:-production}"
PREPARE_REFERENCE="${PREPARE_REFERENCE:-0}"
OUTPUT_DIR="var/validation-vps/recette-mvp-finale"

mkdir -p "${OUTPUT_DIR}"

printf '== Commit candidat ==\n'
git status --short
if [[ -n "$(git status --porcelain)" ]]; then
  echo "L'arbre Git doit être propre avant qualification." >&2
  exit 1
fi
CANDIDATE_SHA="$(git rev-parse HEAD)"
printf '%s\n' "${CANDIDATE_SHA}" | tee "${OUTPUT_DIR}/candidate-sha.txt"

if [[ "${PREPARE_REFERENCE}" == "1" ]]; then
  printf '== Construction du dossier REF-MVP-01 ==\n'
  python deployment/scripts/vps/projet_reference.py \
    --base-url "${BASE_URL}" \
    --email "${RECETTE_ENGINEER_EMAIL}" \
    --password "${RECETTE_ENGINEER_PASSWORD}" \
    --approver-email "${RECETTE_APPROVER_EMAIL}" \
    --approver-password "${RECETTE_APPROVER_PASSWORD}" \
    | tee "${OUTPUT_DIR}/projet-reference.log"
fi

printf '== Recette fonctionnelle automatisable ==\n'
RECETTE_ARGS=(
  --base-url "${BASE_URL}"
  --email "${RECETTE_ENGINEER_EMAIL}"
  --password "${RECETTE_ENGINEER_PASSWORD}"
  --project-code REF-MVP-01
  --output-dir "${OUTPUT_DIR}"
)
if [[ -n "${SECONDARY_BASE_URL:-}" ]]; then
  : "${SECONDARY_EMAIL:?SECONDARY_EMAIL est requis avec SECONDARY_BASE_URL}"
  : "${SECONDARY_PASSWORD:?SECONDARY_PASSWORD est requis avec SECONDARY_BASE_URL}"
  RECETTE_ARGS+=(
    --secondary-base-url "${SECONDARY_BASE_URL}"
    --secondary-email "${SECONDARY_EMAIL}"
    --secondary-password "${SECONDARY_PASSWORD}"
  )
fi
python deployment/scripts/vps/recette_mvp_finale.py "${RECETTE_ARGS[@]}" \
  | tee "${OUTPUT_DIR}/recette.log"

printf '== Qualification complète du candidat ==\n'
./deployment/scripts/vps/qualify.sh "${PROFILE}" \
  | tee "${OUTPUT_DIR}/qualification.log"

printf '== Vérification de stabilité du SHA ==\n'
AFTER_SHA="$(git rev-parse HEAD)"
if [[ "${AFTER_SHA}" != "${CANDIDATE_SHA}" ]]; then
  echo "Le HEAD a changé pendant la qualification : ${CANDIDATE_SHA} -> ${AFTER_SHA}." >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "La qualification a laissé des modifications suivies dans l'arbre Git." >&2
  git status --short >&2
  exit 1
fi

cat <<EOF

Portes techniques terminées pour ${CANDIDATE_SHA}.

Reste volontairement MANUEL avant v1.0.0-mvp :
  1. examen et signature de docs/validation/acceptation_ingenieur_mvp.md ;
  2. correction de toute réserve S0/S1/S2 ;
  3. désignation de la clé RELEASE_SIGNING_KEY ;
  4. génération/signature des artefacts et création du tag signé.

Ne créez pas v1.0.0-mvp tant que ces quatre points ne sont pas fermés.
EOF
