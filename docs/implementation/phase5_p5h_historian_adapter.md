# Phase 5 — P5-H Adaptateur historian read-only générique

Références : D09, D12, D15, D17 et D20.

## Implémentation

`hydro_api.industrial.historian` définit un contrat indépendant de tout fournisseur :

- fenêtre de lecture timezone-aware, normalisée en UTC ;
- tag externe ;
- valeur numérique source et unité source ;
- `SourceTimestamp` et `ServerTimestamp` facultatif ;
- qualité `good / uncertain / bad` ;
- référence de provenance ;
- séquence facultative ;
- diagnostics de doublons et violations d'ordre source.

La qualité `bad` reste archivable mais n'est pas déclarée utilisable par l'analytique.

## Architecture

Les SDK PI/AVEVA, IP.21, PHD, OPC HDA ou autres ne sont pas importés dans le cœur. Un adaptateur fournisseur futur doit convertir sa réponse vers ce contrat, puis la couche d'ingestion V1 résout le tag PETROLE, conserve le brut et produit la projection SI versionnée.

## Limites

- aucun identifiant fournisseur n'est inventé ;
- aucun accès réseau historian n'est simulé ;
- aucun write ni acquittement ;
- aucune qualité propriétaire n'est silencieusement convertie sans table de mapping versionnée.

La connexion réelle reste soumise à la revue OT et aux credentials/certificats du site.
