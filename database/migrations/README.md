# Migrations de base de données

Alembic gère le schéma PostgreSQL/PostGIS. Depuis le conteneur de développement :

    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml exec api alembic upgrade head

Une migration est obligatoire pour toute modification du modèle relationnel. Les tables
de calcul conservent les entrées canoniques et résultats immuables ; aucune migration ne
doit réécrire ces données sans procédure de contrôle dédiée.
