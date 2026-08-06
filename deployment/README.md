# Déploiement

La procédure complète pour installation, transfert des données, développement avec volumes,
TLS, qualification et passage en production sur Ubuntu est décrite dans
[`VPS.md`](VPS.md).

Les exemples emploient la syntaxe Compose v2 `docker compose`. Si votre installation expose
Compose v2 sous la commande autonome `docker-compose`, remplacez simplement la commande dans
les exemples ; les scripts VPS détectent les deux formes automatiquement.

## Déploiement local

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

## Instance mono-organisation et traçabilité de release

Le Compose de production active par défaut `HYDRO_DEPLOYMENT_MODE=single_org`.
Le premier bootstrap crée l'exploitant défini par
`HYDRO_DEFAULT_ORGANIZATION_NAME` et `HYDRO_DEFAULT_ORGANIZATION_SLUG`; un
`HYDRO_DEFAULT_ORGANIZATION_ID` peut être fixé pour une instance déjà initialisée.
Les colonnes d'organisation restent en base, mais les créations et listes API sont
liées côté serveur à cet espace unique.

La CI de release doit renseigner `HYDRO_BUILD_GIT_SHA`, `HYDRO_BUILD_REF` et
`HYDRO_BUILD_DATE` lors de la construction de l'image. L'API publie ces valeurs,
la version du moteur et la migration attendue dans `/api/v1/health` et
`/api/v1/version`. Une image avec `unknown` ne doit pas être promue en production.

## Sauvegarde et restauration locales

La sauvegarde cohérente regroupe PostgreSQL et le stockage objet dans un dossier horodaté. L'API,
le worker et MinIO sont arrêtés brièvement pour empêcher une écriture entre les deux captures, puis
redémarrés automatiquement. Chaque archive est contrôlée puis accompagnée d'un manifeste SHA-256 :

    powershell -ExecutionPolicy Bypass -File deployment/scripts/backup.ps1

La restauration remplace intégralement la base et les fichiers. Elle exige donc une autorisation explicite, vérifie les empreintes avant toute suppression, applique les migrations restantes, puis redémarre l'API et le processus de calcul :

    powershell -ExecutionPolicy Bypass -File deployment/scripts/restore.ps1 `
      -BackupDirectory var/backups/AAAAMMJJTHHMMSSZ `
      -ConfirmRestore

Le résultat de l'exercice est écrit dans « restore-result.json ». Conserver au moins une copie chiffrée hors de la machine pour respecter l'objectif de reprise après incident.
