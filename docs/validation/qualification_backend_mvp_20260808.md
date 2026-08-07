# Qualification de la plateforme — 8 août 2026

## Objet

Cette campagne clôt les lots de fermeture F01 à F07 définis avec l'audit
technique : instance mono-exploitant, ressources et réseau typés, résultats
détaillés et graphiques, transfert piloté par le réseau, entrées-sorties de
données, approbation des simulations et voie de résolution Pyomo.

Elle qualifie un **MVP logiciel**. Elle n'établit ni certification ASME, API ou
ISO, ni autorisation d'exploiter une installation réelle. La recette par un
ingénieur métier extérieur à l'équipe reste la dernière porte ouverte.

## Preuves exécutées

| Contrôle | Résultat |
|---|---:|
| Suite backend Docker (`-m "not slow"`) | **540 tests réussis** |
| Validation scientifique | **41/41** |
| Empreinte reproductible des résultats | `6973bd97cbbdbd38d64d95dbbedf44bd630e10cacf380a0cc2fda6651ff98e3a` |
| Tests unitaires web | **45 réussis** |
| Playwright bureau et mobile | **33 réussis** |
| ruff format, ruff check, mypy | verts |
| TypeScript et build Vite | sans erreur |
| `npm audit` (high et au-delà) | **0 vulnérabilité** |
| Gitleaks (161 commits) | **aucun secret** |
| Trivy image API production | **0 HIGH/CRITICAL corrigeable** |
| Trivy image web production | **0 HIGH/CRITICAL corrigeable** |
| OWASP ZAP baseline sur le domaine public | **0 FAIL**, 60 PASS, 7 avertissements |
| Sauvegarde PostgreSQL | dump 110 859 octets, 254 entrées |
| Restauration sur base jetable | **35 tables**, tête `9f3b6e0d5c17` |
| HTTPS public `ready` | HTTP 200 |

L'empreinte scientifique est **inchangée** depuis la campagne du 7 août : la
refonte du transfert, l'ajout de la voie Pyomo et l'approbation des calculs
n'ont modifié aucun résultat physique. C'est la propriété que l'empreinte
reproductible sert précisément à démontrer.

## Avertissements ZAP retenus

Les sept avertissements sont ceux d'une application à page unique servie
derrière un nginx de terminaison : en-têtes `Cross-Origin-Embedder-Policy` et
`Cross-Origin-Opener-Policy` absents, divulgation d'horodatage dans le bundle
JavaScript, détection d'application web moderne. Aucun n'est bloquant et aucun
ne révèle de donnée métier. Ils sont conservés tels quels plutôt que masqués.

## Schéma de base

Quatre migrations ont été appliquées depuis la version précédente :

| Révision | Objet |
|---|---|
| `5e9a1c7b2f48` | filiation hydraulique des transferts |
| `7c2d4f8b1a35` | séparation des données importables et des pièces jointes |
| `9f3b6e0d5c17` | décision humaine sur une simulation |

Toutes sont additives et nullables : les enregistrements antérieurs restent
lisibles sans reprise.

## État déployé

`https://petrole.distesage.com` sert exactement `main`. L'identité du build est
publiée par `GET /api/v1/version` : SHA Git, référence, date de construction,
version du noyau scientifique et révision de migration attendue.

Mode de déploiement : `single_org`, exploitant **PETROLE / DISTESAGE**,
identifiant figé dans l'environnement du serveur.

## Ce qui reste ouvert

- **Lot F03** — l'éditeur graphique du réseau reste une vue : la modélisation se
  fait par formulaires typés, complets mais non graphiques.
- **Recette métier** — aucun ingénieur extérieur à l'équipe n'a déroulé le
  parcours complet. La définition du MVP l'exige explicitement.
- **Données réelles** — aucune courbe constructeur, table de jaugeage certifiée
  ni analyse laboratoire n'est chargée.
- **Conformité normative** — la matrice clause par clause n'est pas établie ; la
  plateforme enregistre et évalue des règles, elle ne prononce pas de conformité.
- **Isolation** — aucune politique PostgreSQL de sécurité au niveau des lignes ;
  l'isolation reste applicative.

## Limite de portée

Un MVP logiciel qualifié n'est pas une autorisation d'exploiter. Les résultats
produits par la plateforme sont des éléments d'étude soumis au jugement d'un
ingénieur habilité.
