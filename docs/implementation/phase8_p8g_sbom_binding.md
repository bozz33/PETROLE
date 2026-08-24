# Phase 8 — P8-G Binding du SBOM au manifeste de release

Références : D17 Phase 8, D18 et la chaîne de release PETROLE.

## Implémentation

`hydro_shared.release_provenance.verify_sbom_bytes(...)` vérifie que les octets d'un SBOM correspondent exactement à `ReleaseManifest.sbom_sha256`.

Règles :

- une release sans `sbom_sha256` ne peut jamais retourner une vérification SBOM positive ;
- toute modification d'un octet du SBOM invalide le binding ;
- le manifeste canonique continue d'embarquer le hash du SBOM et les hashes/taille des autres artefacts ;
- les clés de signature restent hors de l'application.

## Limite volontaire

Le dépôt ne sélectionne pas encore un générateur SBOM CycloneDX/SPDX particulier. PETROLE ne fabrique donc pas un faux SBOM « standard » à partir d'un format maison. Le format et le générateur devront être choisis explicitement dans la chaîne de release, puis leur sortie sera liée au manifeste par cette empreinte.

Le hash prouve l'identité des octets fournis ; il ne prouve ni l'exhaustivité du SBOM, ni l'absence de vulnérabilité, ni une certification logicielle/industrielle.
