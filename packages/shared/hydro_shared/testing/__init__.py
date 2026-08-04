"""Infrastructure partagée réservée aux tests d'intégration."""

from hydro_shared.testing.postgres import reset_public_tables

__all__ = ["reset_public_tables"]
