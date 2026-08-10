# Phase 8 — Gouvernance du cycle de vie des certificats

Références : D15, D17 et D18.

## Implémentation

`hydro_shared.certificate_lifecycle` suit les métadonnées nécessaires à l'exploitation :

- référence du certificat ;
- empreinte SHA-256 ;
- références sujet/émetteur ;
- `not_before` / `not_after` timezone-aware ;
- provenance de l'inventaire PKI ;
- fenêtre d'anticipation explicitement définie par la politique d'exploitation.

L'évaluation retourne `not_yet_valid`, `valid`, `due` ou `expired` et le temps restant avant expiration.

## Limites

Cette brique ne valide pas la signature cryptographique, la chaîne de certification, la révocation OCSP/CRL ou la confiance d'un endpoint. Ces contrôles appartiennent au moteur TLS/OPC UA et à la PKI du déploiement.

Un certificat `valid` au sens temporel n'est donc pas automatiquement un certificat de confiance.

## Gate

Les certificats réels, la CA, la trust-list, la rotation et les alertes d'expiration doivent être intégrés à l'environnement de staging/production et testés pendant la qualification OT/industrialisation.
