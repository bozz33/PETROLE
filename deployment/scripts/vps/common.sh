#!/usr/bin/env bash

set -Eeuo pipefail

VPS_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly VPS_SCRIPT_DIR
VPS_REPOSITORY_ROOT="$(cd -- "${VPS_SCRIPT_DIR}/../../.." && pwd)"
readonly VPS_REPOSITORY_ROOT

VPS_MODE="development"
VPS_ENV_FILE="${VPS_REPOSITORY_ROOT}/deployment/.env.vps"
VPS_COMPOSE_ARGUMENTS=()
VPS_COMPOSE_COMMAND=()

detecter_compose() {
    if command -v docker >/dev/null 2>&1 \
        && docker compose version >/dev/null 2>&1; then
        VPS_COMPOSE_COMMAND=(docker compose)
        return 0
    fi

    if command -v docker-compose >/dev/null 2>&1 \
        && docker-compose version >/dev/null 2>&1; then
        VPS_COMPOSE_COMMAND=(docker-compose)
        return 0
    fi

    echo "Docker Compose v2 est requis (commande 'docker compose' ou 'docker-compose')." >&2
    return 2
}

initialiser_contexte_vps() {
    VPS_MODE="${1:-development}"
    VPS_ENV_FILE="${2:-${VPS_REPOSITORY_ROOT}/deployment/.env.vps}"

    case "${VPS_MODE}" in
        development|production) ;;
        *)
            echo "Mode inconnu : ${VPS_MODE}. Utilisez development ou production." >&2
            return 2
            ;;
    esac

    if [[ ! -f "${VPS_ENV_FILE}" ]]; then
        echo "Fichier d'environnement introuvable : ${VPS_ENV_FILE}" >&2
        return 2
    fi
    VPS_ENV_FILE="$(realpath "${VPS_ENV_FILE}")"
    detecter_compose

    VPS_COMPOSE_ARGUMENTS=(
        --env-file "${VPS_ENV_FILE}"
        -f "${VPS_REPOSITORY_ROOT}/deployment/docker-compose.yml"
    )
    if [[ "${VPS_MODE}" == "development" ]]; then
        VPS_COMPOSE_ARGUMENTS+=(
            -f "${VPS_REPOSITORY_ROOT}/deployment/docker-compose.dev.yml"
        )
    fi
    VPS_COMPOSE_ARGUMENTS+=(
        -f "${VPS_REPOSITORY_ROOT}/deployment/docker-compose.vps.yml"
    )
}

compose_vps() {
    "${VPS_COMPOSE_COMMAND[@]}" "${VPS_COMPOSE_ARGUMENTS[@]}" "$@"
}

valeur_environnement() {
    local nom="$1"
    local ligne
    ligne="$(grep -E "^${nom}=" "${VPS_ENV_FILE}" | tail -n 1 || true)"
    printf '%s' "${ligne#*=}"
}

exiger_commande() {
    local commande="$1"
    if ! command -v "${commande}" >/dev/null 2>&1; then
        echo "Commande requise absente : ${commande}" >&2
        return 2
    fi
}

attendre_postgresql() {
    local _tentative
    for _tentative in $(seq 1 60); do
        if compose_vps exec -T postgres sh -c \
            'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    echo "PostgreSQL n'est pas prêt après 120 secondes." >&2
    return 1
}

attendre_api_locale() {
    local port_api _tentative
    port_api="$(valeur_environnement API_PORT)"
    port_api="${port_api:-8000}"
    for _tentative in $(seq 1 60); do
        if curl --fail --silent --show-error --max-time 5 \
            "http://127.0.0.1:${port_api}/api/v1/health/ready" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    echo "L'API locale n'est pas prête après 120 secondes." >&2
    return 1
}
