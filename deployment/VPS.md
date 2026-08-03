# Déploiement et développement sur VPS

Cette procédure cible un VPS Ubuntu récent, un utilisateur non privilégié disposant de `sudo`,
un domaine public et une clé SSH. Elle conserve le rechargement automatique pendant le
développement, puis permet de passer aux images immuables sans changer les données.

## 1. Préparer le DNS et le réseau

Créer un enregistrement DNS `A` — et `AAAA` si IPv6 est correctement configuré — vers le VPS.
Le certificat TLS ne pourra être délivré qu'après propagation du DNS et accessibilité publique
des ports 80 et 443.

Autoriser uniquement :

- SSH, idéalement limité aux adresses d'administration ;
- TCP 80 pour le défi ACME et la redirection HTTPS ;
- TCP 443 et UDP 443 pour HTTPS et HTTP/3.

Ne pas ouvrir publiquement 5173, 8000, 5432, 9000 ou 9001. La configuration Compose les lie à
`127.0.0.1`.

## 2. Installer les prérequis

Depuis le dossier personnel, effectuer un clone de bootstrap séparé du futur dossier applicatif :

```bash
git clone https://github.com/bozz33/PETROLE.git "$HOME/petrole-bootstrap"
cd "$HOME/petrole-bootstrap"
sudo ./deployment/scripts/vps/bootstrap-ubuntu.sh "$USER" /opt/petrole
```

Le script configure le dépôt APT officiel de Docker, installe Docker Engine, le plugin Compose,
Git et les utilitaires requis, puis prépare `/opt/petrole`. Il ne modifie ni SSH ni le pare-feu :
ces règles dépendent de l'hébergeur et doivent rester accessibles pendant leur configuration.

Fermer puis rouvrir la session SSH pour appliquer l'appartenance au groupe `docker`. Vérifier :

```bash
docker version
docker compose version
```

Les scripts VPS acceptent aussi l'installation Compose v2 qui fournit la commande autonome
`docker-compose` au lieu du sous-programme `docker compose` ; ils sélectionnent automatiquement
la commande disponible. Pour les vérifications manuelles ci-dessous, utiliser la même forme.

## 3. Installer le dépôt définitif

```bash
git clone https://github.com/bozz33/PETROLE.git /opt/petrole
cd /opt/petrole
git switch main
git pull --ff-only
```

Pour un dépôt privé, utiliser une clé de déploiement en lecture ou l'authentification Git choisie.
Ne jamais copier un jeton Git dans le dépôt ou le fichier d'environnement.

## 4. Créer la configuration secrète

```bash
cd /opt/petrole
./deployment/scripts/vps/generate-env.sh \
  petrole.exemple.com administrateur@exemple.com
nano deployment/.env.vps
chmod 600 deployment/.env.vps
```

Remplacer le domaine, l'adresse ACME et les valeurs métier. Les secrets aléatoires sont générés
localement. `deployment/.env.vps` est ignoré par Git ; ne jamais le transférer depuis un poste
partagé et ne jamais le commiter.

## 5. Démarrer avec rechargement automatique

```bash
./deployment/scripts/vps/deploy.sh development
```

Le mode `development` ajoute `docker-compose.dev.yml` : la racine du dépôt est montée dans les
conteneurs Python et `apps/web` dans Vite. Les changements sont visibles automatiquement. Après
une modification des dépendances, relancer le script pour reconstruire les images.

Contrôles :

```bash
docker compose --env-file deployment/.env.vps \
  -f deployment/docker-compose.yml \
  -f deployment/docker-compose.dev.yml \
  -f deployment/docker-compose.vps.yml ps
curl --fail https://<domaine>/api/v1/health/ready
```

## 6. Transférer les données locales

Depuis Windows, après commit et push du code :

```powershell
powershell -ExecutionPolicy Bypass -File deployment/scripts/prepare-vps-transfer.ps1 `
  -VpsHost <adresse-ou-domaine> `
  -VpsUser <utilisateur> `
  -RemoteRoot /opt/petrole
```

Le script exige un dépôt suivi propre, compare le commit local à `origin/main`, crée une
sauvegarde locale si nécessaire, met le clone VPS à jour en avance rapide et transfère uniquement
la sauvegarde PostgreSQL/MinIO. Les secrets ne sont pas transférés.

Sur le VPS, restaurer explicitement :

```bash
cd /opt/petrole
./deployment/scripts/vps/restore.sh --confirm-replacement \
  /opt/petrole/var/incoming-backup/<nom-de-sauvegarde> \
  development
```

La restauration remplace les données. Le script vérifie d'abord toutes les empreintes SHA-256,
attend PostgreSQL, applique les migrations puis vérifie l'état de l'API.

## 7. Qualifier le VPS

```bash
./deployment/scripts/vps/qualify.sh development
```

La campagne exécute contrôles Python et frontend, tests rapides et lents, validation scientifique,
charge API sur une instance isolée sans rechargement automatique, audits des dépendances, détection
de secrets, analyses Trivy des images, contrôle ZAP et disponibilité publique. L'instance de charge
utilise les vraies dépendances PostgreSQL/MinIO, sans modifier leur contenu. Les preuves sont écrites
sous `var/validation-vps/<horodatage>`.

Un avertissement ZAP n'est pas automatiquement ignoré : examiner son rapport. Toute vulnérabilité
réelle doit être corrigée ou documentée avec justification, impact et échéance.

## 8. Sauvegarder et superviser

Sauvegarde manuelle :

```bash
./deployment/scripts/vps/backup.sh development
```

Le script arrête brièvement API, worker et MinIO, produit les deux archives et redémarre uniquement
les services qui étaient actifs. Cette fenêtre de maintenance garantit une capture cohérente entre
base et stockage objet.

Programmer ensuite cette commande avec un minuteur `systemd` ou `cron`, contrôler le code retour,
chiffrer une copie hors VPS et tester régulièrement la restauration. Conserver les journaux Docker,
l'espace disque, l'expiration TLS et l'état `/api/v1/health/ready` sous surveillance.

## 9. Coexister avec le frontend parallèle

Utiliser une branche ou un worktree distinct par chantier. Avant fusion :

```bash
git fetch origin
git status --short
git worktree list
```

Ne jamais forcer une branche partagée. Fusionner le frontend après revue des contrats API et lancer
typecheck, tests, E2E et build. Le montage de volume du mode développement évite une reconstruction
à chaque édition.

## 10. Passer en mode production

Après qualification du code et arrêt du besoin de rechargement automatique :

```bash
./deployment/scripts/vps/backup.sh development
./deployment/scripts/vps/deploy.sh production
./deployment/scripts/vps/qualify.sh production
```

Le mode `production` copie le code dans les images et n'ajoute pas les volumes de développement.
Les volumes PostgreSQL, MinIO et Caddy restent les mêmes. `HYDRO_WEB_CONCURRENCY` règle le nombre
de processus HTTP ; la valeur initiale `2` correspond au minimum conseillé pour la recette de
25 utilisateurs. L'ajuster après mesure selon les vCPU et la mémoire du VPS.

## 11. Limites de cette préparation

Les scripts préparent et sécurisent le déploiement applicatif, mais ne choisissent pas le fournisseur,
ne créent pas le VPS, ne configurent pas les règles réseau propres à l'hébergeur et ne détiennent pas
les clés SSH ou le domaine. Le déploiement public final nécessite ces paramètres.

## 12. Références d'exploitation

- [installation officielle de Docker Engine sur Ubuntu](https://docs.docker.com/engine/install/ubuntu/) ;
- [installation officielle du plugin Docker Compose](https://docs.docker.com/compose/install/linux/) ;
- [HTTPS automatique avec Caddy](https://caddyserver.com/docs/automatic-https) ;
- [directive `reverse_proxy` de Caddy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
