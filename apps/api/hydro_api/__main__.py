"""Démarrage direct de l'API avec la commande python -m hydro_api."""

from __future__ import annotations

import uvicorn

from hydro_api.config import get_settings


def main() -> None:
    """Démarre Uvicorn avec la configuration validée de l'environnement."""

    settings = get_settings()
    uvicorn.run(
        "hydro_api.application:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
