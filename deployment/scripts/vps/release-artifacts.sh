#!/usr/bin/env bash
# Produit les artefacts de traçabilité d'une release : nomenclature logicielle
# des images, empreintes des artefacts, et signature lorsque le mainteneur
# fournit une clé.
#
# La signature n'est jamais improvisée : sans clé explicitement désignée, le
# script produit les nomenclatures et les empreintes, puis signale clairement
# que les artefacts ne sont pas signés. Générer une clé engage une identité et
# relève d'une décision humaine, pas d'un script de build.
#
# Utilisation :
#   deployment/scripts/vps/release-artifacts.sh v1.0.0-mvp [dossier-de-sortie]
#
# Variables :
#   RELEASE_SIGNING_KEY  identifiant de clé GPG utilisé pour signer les empreintes.

set -euo pipefail

TAG="${1:?Indiquez le tag de release, par exemple v1.0.0-mvp}"
OUTPUT_DIR="${2:-var/release/${TAG}}"
IMAGES=("petrole-api:latest" "petrole-web:latest")

mkdir -p "${OUTPUT_DIR}"

echo "== Identité de la release =="
git rev-parse "${TAG}^{commit}" > "${OUTPUT_DIR}/commit.txt"
git show -s --format=%cI "${TAG}^{commit}" > "${OUTPUT_DIR}/date.txt"
echo "Commit : $(cat "${OUTPUT_DIR}/commit.txt")"

echo "== Nomenclature logicielle des images =="
for image in "${IMAGES[@]}"; do
  safe_name="${image//[:\/]/-}"
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy:latest image \
    --format cyclonedx \
    --quiet \
    --output /dev/stdout \
    "${image}" > "${OUTPUT_DIR}/sbom-${safe_name}.cdx.json"
  echo "  ${image} → sbom-${safe_name}.cdx.json"

  # L'empreinte de l'image rend l'artefact déployé identifiable sans ambiguïté,
  # indépendamment d'une étiquette qui peut être réattribuée.
  docker image inspect --format '{{.Id}}' "${image}" \
    > "${OUTPUT_DIR}/image-${safe_name}.digest"
done

echo "== Empreintes des artefacts =="
( cd "${OUTPUT_DIR}" && sha256sum ./*.json ./*.digest ./*.txt > SHA256SUMS )
cat "${OUTPUT_DIR}/SHA256SUMS"

echo "== Signature =="
if [[ -n "${RELEASE_SIGNING_KEY:-}" ]]; then
  gpg --local-user "${RELEASE_SIGNING_KEY}" \
      --armor --detach-sign \
      --output "${OUTPUT_DIR}/SHA256SUMS.asc" \
      "${OUTPUT_DIR}/SHA256SUMS"
  echo "Empreintes signées par ${RELEASE_SIGNING_KEY}."
  echo "Signez également le tag : git tag -s ${TAG} -f"
else
  echo "RELEASE_SIGNING_KEY n'est pas défini : les artefacts NE SONT PAS signés."
  echo "Une release destinée à un tiers doit être signée avant diffusion."
  exit 2
fi
