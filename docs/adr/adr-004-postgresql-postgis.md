# ADR-004 — PostgreSQL/PostGIS comme source de vérité

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

Le produit manipule des données relationnelles fortement contraintes, des géométries de tracé et, à terme, des séries temporelles.

## Décision

**PostgreSQL** avec l'extension **PostGIS** est la source de vérité unique. Les séries temporelles du MVP sont stockées dans PostgreSQL partitionné ; une migration vers TimescaleDB n'interviendra qu'après mesure d'un volume réel.

## Conséquences

Positif : transactions, contraintes d'intégrité, index spatiaux et écosystème mature dans un seul socle.

Négatif : PostGIS impose une image de base spécifique ; assumé et fourni dans le Docker Compose.

Évolution : réplication, partitionnement et haute disponibilité sans changement de technologie.
