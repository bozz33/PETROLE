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

## Sauvegarde et restauration locales

La sauvegarde cohérente regroupe PostgreSQL et le stockage objet dans un dossier horodaté. Chaque archive est contrôlée puis accompagnée d'un manifeste SHA-256 :

    powershell -ExecutionPolicy Bypass -File deployment/scripts/backup.ps1

La restauration remplace intégralement la base et les fichiers. Elle exige donc une autorisation explicite, vérifie les empreintes avant toute suppression, applique les migrations restantes, puis redémarre l'API et le processus de calcul :

    powershell -ExecutionPolicy Bypass -File deployment/scripts/restore.ps1 `
      -BackupDirectory var/backups/AAAAMMJJTHHMMSSZ `
      -ConfirmRestore

Le résultat de l'exercice est écrit dans « restore-result.json ». Conserver au moins une copie chiffrée hors de la machine pour respecter l'objectif de reprise après incident.
