# Phase 5 — Mapping qualité fournisseur → PETROLE

Références : D09, D12, D15 et D17.

## Implémentation

`hydro_api.industrial.quality_mapping` définit une table versionnée de correspondance entre un code qualité fournisseur et le contrat PETROLE : `good`, `uncertain`, `bad`, `substituted`, `estimated`.

Chaque règle conserve :

- code source exact ;
- qualité cible ;
- provenance de la règle ;
- fournisseur ;
- version du registre.

Le résultat conserve simultanément le code externe et la qualité normalisée, afin de permettre audit et reprocessing.

## Règle non négociable

Un code externe absent du registre provoque un refus explicite. Il n'existe aucun fallback vers `good` ou `uncertain`.

Les tables réelles seront produites à partir de la documentation du fournisseur/historian retenu et revues avant connexion au site.
