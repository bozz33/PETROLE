# Matrice de conformité normative du MVP

- Date de vérification publique : 3 août 2026
- Portée : fonctions logicielles du backend, sans certification d'installation

## Éditions publiquement vérifiées

| Référence | État public vérifié | Source officielle |
|---|---|---|
| ASME B31.4 | édition 2025 | https://www.asme.org/codes-standards/find-codes-standards/pipeline-transportation-systems-for-liquids-and-slurries |
| ISO 13623 | édition 2017, confirmée en 2026 | https://www.iso.org/standard/61251.html |
| ISO 13623/Amd 1 | amendement 2024 | https://www.iso.org/standard/83015.html |
| API 610 | 12e édition publiquement confirmée ; 13e encore visible en processus de comité | https://www.api.org/products-and-services/standards/important-standards-announcements/rp697 |
| API 650 | 14e édition publiée en août 2025 | https://www.api.org/products-and-services/api-monogram-and-apiqr/latest-updates |

Les pages publiques donnent le domaine et l'édition, pas l'ensemble des exigences protégées
par licence. La matrice clause par clause doit partir des exemplaires légalement acquis par
l'opérateur.

## Capacités de gouvernance présentes

| Contrôle logiciel | État |
|---|---|
| Références de normes versionnées par organisation | Implémenté et testé |
| Jeux de règles séparés du solveur physique | Implémenté et testé |
| Règles en brouillon, approuvées ou archivées | Implémenté et testé |
| Approbation experte obligatoire avant activation | Implémenté et testé |
| Jeu approuvé immuable | Implémenté et testé |
| Clause source, sévérité, message et limite traçables | Implémenté et testé |
| Absence de règle traitée comme conformité | Interdite et testée |
| Règle bloquante non conforme | Bloque l'approbation du rapport |
| Pression absolue, unités SI et marge MAOP | Implémentées et testées |
| Aucune commande SCADA dans le MVP | Respecté par l'architecture actuelle |

## Verdict

La plateforme fournit les mécanismes nécessaires pour appliquer des règles officiellement
validées, mais le dépôt ne contient pas de paquet réglementaire prétendant reproduire ASME,
API, ISO, IEC ou ISA. Ce choix évite une conformité fictive et la redistribution non autorisée
de textes protégés.

Le statut correct est donc : **architecture prête pour la conformité, conformité réglementaire
non certifiée**. Pour passer à un statut contractuel, il faut sélectionner le pays et le site,
acquérir les éditions applicables, faire transcrire et relire chaque clause par un expert,
approuver le jeu de règles, exécuter les cas d'acceptation et obtenir la validation de
l'ingénieur responsable.
