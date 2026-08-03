#!/usr/bin/env bash

set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Exécutez ce script avec sudo sur Ubuntu." >&2
    exit 2
fi

if [[ ! -r /etc/os-release ]]; then
    echo "Le système ne fournit pas /etc/os-release." >&2
    exit 2
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
    echo "Ce bootstrap est validé uniquement pour Ubuntu ; système détecté : ${ID:-inconnu}." >&2
    exit 2
fi

utilisateur_cible="${1:-${SUDO_USER:-}}"
if [[ -z "${utilisateur_cible}" || "${utilisateur_cible}" == "root" ]]; then
    echo "Indiquez le compte non privilégié qui exploitera le dépôt." >&2
    echo "Exemple : sudo bash bootstrap-ubuntu.sh deploy" >&2
    exit 2
fi

racine_projet="${2:-/opt/petrole}"
if [[ ! "${racine_projet}" =~ ^/opt/[A-Za-z0-9._/-]+$ || "${racine_projet}" == *..* ]]; then
    echo "Le dossier projet doit être un chemin précis situé sous /opt." >&2
    exit 2
fi
if ! id "${utilisateur_cible}" >/dev/null 2>&1; then
    echo "Le compte ${utilisateur_cible} n'existe pas." >&2
    exit 2
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl git gnupg jq openssl rsync

if ! command -v docker >/dev/null 2>&1; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    architecture="$(dpkg --print-architecture)"
    nom_version="${UBUNTU_CODENAME:-${VERSION_CODENAME}}"
    cat >/etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${nom_version}
Components: stable
Architectures: ${architecture}
Signed-By: /etc/apt/keyrings/docker.asc
EOF
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

systemctl enable --now docker
usermod -aG docker "${utilisateur_cible}"

groupe_cible="$(id -gn "${utilisateur_cible}")"
install -d -m 0750 -o "${utilisateur_cible}" -g "${groupe_cible}" "${racine_projet}"

docker version >/dev/null
docker compose version

cat <<EOF
Bootstrap terminé.

Actions administrateur restantes :
1. reconnecter ${utilisateur_cible} pour appliquer le groupe docker ;
2. autoriser uniquement SSH, TCP 80, TCP 443 et UDP 443 dans le pare-feu du fournisseur ;
3. utiliser une clé SSH, puis désactiver l'authentification SSH par mot de passe ;
4. pointer le DNS du domaine vers ce VPS.
EOF
