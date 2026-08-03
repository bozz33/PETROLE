"""Test de charge HTTP local du backend MVP.

Le scénario représente 25 utilisateurs simultanés consultant les ressources courantes hors
calcul. Chaque utilisateur parcourt santé, disponibilité, statut d'authentification,
organisations, projets et rapports. Le verdict applique NFR-PERF-003 et NFR-PERF-005 : aucune
erreur HTTP et percentile 95 inférieur à deux secondes.

Exemple :
    python tests/qualification/api_load.py --output var/validation/charge_api.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

DEFAULT_PATHS = (
    "/api/v1/health",
    "/api/v1/health/ready",
    "/api/v1/auth/status",
    "/api/v1/organizations",
    "/api/v1/projects",
    "/api/v1/reports",
)


@dataclass(frozen=True, slots=True)
class LoadResult:
    """Mesures agrégées d'une campagne de charge."""

    started_at: str
    base_url: str
    concurrent_users: int
    requests_per_user: int
    request_count: int
    error_count: int
    duration_s: float
    throughput_request_s: float
    minimum_s: float
    median_s: float
    p95_s: float
    maximum_s: float
    passed: bool


async def _virtual_user(
    client: httpx.AsyncClient,
    user_index: int,
    requests_per_user: int,
) -> list[tuple[float, int]]:
    observations: list[tuple[float, int]] = []
    for request_index in range(requests_per_user):
        path = DEFAULT_PATHS[(user_index + request_index) % len(DEFAULT_PATHS)]
        started = time.perf_counter()
        try:
            response = await client.get(path)
            status_code = response.status_code
        except httpx.HTTPError:
            status_code = 0
        observations.append((time.perf_counter() - started, status_code))
    return observations


async def run_load(
    base_url: str,
    concurrent_users: int,
    requests_per_user: int,
) -> LoadResult:
    """Exécute la charge et calcule le percentile par rang le plus proche."""

    started_at = datetime.now(UTC).isoformat()
    campaign_started = time.perf_counter()
    limits = httpx.Limits(
        max_connections=max(concurrent_users * 2, 50),
        max_keepalive_connections=max(concurrent_users, 25),
    )
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0, limits=limits) as client:
        warmup = await client.get("/api/v1/health/ready")
        warmup.raise_for_status()
        batches = await asyncio.gather(
            *(
                _virtual_user(client, user_index, requests_per_user)
                for user_index in range(concurrent_users)
            )
        )
    duration_s = time.perf_counter() - campaign_started
    observations = [observation for batch in batches for observation in batch]
    durations = sorted(duration for duration, _ in observations)
    error_count = sum(not 200 <= status_code < 400 for _, status_code in observations)
    p95_index = math.ceil(0.95 * len(durations)) - 1
    median_index = len(durations) // 2
    return LoadResult(
        started_at=started_at,
        base_url=base_url,
        concurrent_users=concurrent_users,
        requests_per_user=requests_per_user,
        request_count=len(observations),
        error_count=error_count,
        duration_s=duration_s,
        throughput_request_s=len(observations) / duration_s,
        minimum_s=durations[0],
        median_s=durations[median_index],
        p95_s=durations[p95_index],
        maximum_s=durations[-1],
        passed=error_count == 0 and durations[p95_index] < 2.0,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test de charge local du backend MVP.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=25)
    parser.add_argument("--requests-per-user", type=int, default=20)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.users < 1 or args.requests_per_user < 1:
        raise SystemExit("Le nombre d'utilisateurs et de requêtes doit être positif.")
    result = asyncio.run(run_load(args.base_url, args.users, args.requests_per_user))
    payload = asdict(result)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
