#!/usr/bin/env bash

set -Eeuo pipefail

# shellcheck source=common.sh
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

mode="${1:-development}"
fichier_env="${2:-${VPS_REPOSITORY_ROOT}/deployment/.env.vps}"
initialiser_contexte_vps "${mode}" "${fichier_env}"
VPS_COMPOSE_ARGUMENTS+=(
    -f "${VPS_REPOSITORY_ROOT}/deployment/docker-compose.qualification.yml"
)

nettoyer_qualification() {
    compose_vps --profile qualification stop qualification-api >/dev/null 2>&1 || true
}
trap nettoyer_qualification EXIT

for commande in docker curl git realpath; do
    exiger_commande "${commande}"
done

QUALIFICATION_UID="$(id -u)"
QUALIFICATION_GID="$(id -g)"
export QUALIFICATION_UID QUALIFICATION_GID

horodatage="$(date --utc +%Y%m%dT%H%M%SZ)"
preuves="${VPS_REPOSITORY_ROOT}/var/validation-vps/${horodatage}"
mkdir -p "${preuves}"
domaine="$(valeur_environnement HYDRO_DOMAIN)"

compose_vps --profile qualification build qualification-api qualification-web
compose_vps --profile qualification run --rm --no-deps qualification-api \
    ruff format --check apps packages tests
compose_vps --profile qualification run --rm --no-deps qualification-api \
    ruff check apps packages tests
compose_vps --profile qualification run --rm --no-deps qualification-api \
    mypy packages apps/api
compose_vps --profile qualification run --rm --no-deps qualification-api \
    pytest -m 'not slow' \
    --cov=packages --cov=apps/api --cov-report=term -q
compose_vps --profile qualification run --rm --no-deps qualification-api \
    pytest -m slow -q -s
compose_vps --profile qualification run --rm --no-deps qualification-api \
    python -m hydro_validation.cli \
    --report "/workspace/var/validation-vps/${horodatage}/rapport-scientifique.md" \
    --json "/workspace/var/validation-vps/${horodatage}/rapport-scientifique.json"
compose_vps --profile qualification up --detach qualification-api
for _tentative in $(seq 1 30); do
    if compose_vps --profile qualification exec -T qualification-api python -c \
        'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health/ready", timeout=2)' \
        >/dev/null 2>&1; then
        break
    fi
    if [[ "${_tentative}" -eq 30 ]]; then
        echo "L'API isolée de qualification n'est pas prête." >&2
        exit 1
    fi
    sleep 2
done
compose_vps --profile qualification exec -T qualification-api \
    python tests/qualification/api_load.py \
    --base-url http://127.0.0.1:8000 \
    --output "/workspace/var/validation-vps/${horodatage}/charge-api.json"
compose_vps --profile qualification stop qualification-api
compose_vps --profile qualification run --rm --no-deps qualification-api \
    python -m pip check
compose_vps --profile qualification run --rm --no-deps qualification-web \
    npm run typecheck
compose_vps --profile qualification run --rm --no-deps qualification-web \
    npm test
compose_vps --profile qualification run --rm --no-deps qualification-web \
    npm run build
compose_vps --profile qualification run --rm --no-deps qualification-web \
    npm audit --audit-level=high --json \
    >"${preuves}/npm-audit.json"

mkdir -p "${preuves}/playwright-results"
docker run --rm --ipc=host \
    -e E2E_BASE_URL="https://${domaine}" \
    -e PLAYWRIGHT_USE_BUNDLED_CHROMIUM=true \
    -v "${VPS_REPOSITORY_ROOT}/apps/web:/workspace:ro" \
    -v hydro_e2e_node_modules:/workspace/node_modules \
    -v "${preuves}/playwright-results:/workspace/test-results" \
    -w /workspace \
    mcr.microsoft.com/playwright:v1.55.1-noble \
    bash -lc 'npm ci && npm run test:e2e'

docker run --rm \
    -v "${VPS_REPOSITORY_ROOT}:/repo" \
    zricethezav/gitleaks:latest detect \
    --source=/repo --config=/repo/.gitleaks.toml --redact \
    --report-format=json --report-path="/repo/var/validation-vps/${horodatage}/gitleaks.json"

image_api="$(compose_vps images --quiet api)"
image_web="$(compose_vps images --quiet web)"
for specification in "api:${image_api}" "web:${image_web}"; do
    nom="${specification%%:*}"
    image="${specification#*:}"
    docker run --rm \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v hydro_trivy_cache:/root/.cache/trivy \
        -v "${preuves}:/reports" \
        aquasec/trivy:latest image \
        --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
        --format json --output "/reports/trivy-${nom}.json" "${image}"
done

set +e
docker run --rm \
    -v "${preuves}:/zap/wrk/:rw" \
    ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
    -t "https://${domaine}" -J zap.json -r zap.html
code_zap=$?
set -e
if [[ "${code_zap}" -eq 1 || "${code_zap}" -ge 3 ]]; then
    echo "OWASP ZAP a retourné un échec bloquant : ${code_zap}." >&2
    exit "${code_zap}"
fi

curl --fail --silent --show-error --max-time 10 \
    "https://${domaine}/api/v1/health/ready" >"${preuves}/ready.json"
git rev-parse HEAD >"${preuves}/commit.txt"
echo "Qualification VPS terminée : ${preuves}"
if [[ "${code_zap}" -eq 2 ]]; then
    echo "OWASP ZAP a produit des avertissements à examiner dans zap.html."
fi
