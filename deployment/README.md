# Déploiement local

## Développement avec rechargement automatique

Premier démarrage, ou après modification des dépendances :

    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml up --build

Démarrages suivants :

    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml up

Le fichier de développement monte la racine du dépôt dans les conteneurs API et calcul sous « /workspace ». Uvicorn surveille « apps/api » et « packages » ; le processus de calcul surveille les mêmes sources avec Watchfiles. Le dossier « apps/web » est monté dans le conteneur Vite, tandis que « node_modules » reste dans un volume nommé. Les modifications Python et TypeScript sont donc prises en compte sans reconstruire les images. Une reconstruction reste nécessaire après une modification des dépendances ou des fichiers Docker.

Sous Docker Desktop pour Windows, « WATCHFILES_FORCE_POLLING » garantit la détection fiable des événements des volumes partagés.

## Arrêt

    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml down

Les volumes nommés PostgreSQL et MinIO sont conservés. Utiliser leur suppression
uniquement lorsqu'une réinitialisation explicite des données locales est souhaitée.

## Déploiement sans montage du code

    docker compose -f deployment/docker-compose.yml up --build -d

Cette commande utilise l'étage « runtime » : code copié dans l'image, processus
non privilégié et rechargement désactivé.
