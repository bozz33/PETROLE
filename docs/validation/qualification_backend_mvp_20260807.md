# Qualification du backend MVP — 7 août 2026

## Objet de la campagne

Cette campagne clôt les corrections de priorité P0 issues de l'audit technique du
tableau de bord et du mode de déploiement : suppression des indicateurs fictifs,
mode mono-organisation, exposition de l'identité de build, et surtout **preuve
scientifique réellement vérifiable** au lieu d'une valeur figée à la main.

Comme les campagnes précédentes, elle qualifie un **MVP logiciel**. Elle
n'établit ni certification ASME, API ou ISO, ni autorisation d'exploiter une
installation réelle.

## Empreinte scientifique reproductible

L'attestation publiée par l'API portait auparavant une empreinte figée dans le
dépôt (`b476c957…`), impossible à reproduire : le condensat était calculé sur un
contenu incluant l'horodatage de la campagne, les durées mesurées et les
caractéristiques de la machine. Deux exécutions consécutives du même code
produisaient donc deux empreintes différentes, et la valeur publiée ne
correspondait plus à aucune exécution vérifiable.

Le dossier de preuve distingue désormais deux condensats :

| Condensat | Contenu | Usage |
|---|---|---|
| `proof_hash` | résultats scientifiques seuls : cas, observations, écarts, tolérances, verdicts, versions de plateforme, de moteur et de schémas | **reproductible** ; identifie le contenu scientifique validé |
| `sha256` | dossier complet : horodatage, durées, interpréteur, système, versions des dépendances | identifie une **exécution** précise, pour la traçabilité |

Une observation peut être déclarée non reproductible (`reproducible=False`)
lorsqu'elle mesure une grandeur dépendante de la machine. Un seul cas est
concerné, `V-020` (« Durée de calcul sous la cible MVP ») : son verdict de
conformité à la limite reste dans l'empreinte, la valeur mesurée en est exclue.

L'attestation servie par `GET /api/v1/health/validation` est produite par la
commande d'exécution elle-même :

```bash
hydro-validate \
  --attestation apps/api/hydro_api/scientific_validation_proof.json \
  --attestation-source docs/validation/qualification_backend_mvp_20260807.md
```

Un test de la suite (`test_attestation_publiee_correspond_a_une_execution_reelle`)
relance les 41 cas et compare le comptage, la version de moteur et l'empreinte à
l'attestation embarquée dans l'image. Toute valeur saisie à la main fait
désormais échouer la qualification avant la mise en production.

## Version du moteur scientifique exposée

`GET /api/v1/version` publiait `long_distance_liquid-0.1.0`, c'est-à-dire
l'identifiant du solveur longue distance, qui ne change pas lorsqu'une équation
ou une corrélation est modifiée. Le champ `scientific_engine_version` expose
maintenant `ENGINE_VERSION` (`hydroliquid-0.1.0`), la version normative du noyau
scientifique, cohérente avec celle inscrite dans le dossier de preuve.

## Preuves exécutées

| Contrôle | Résultat vérifié |
|---|---:|
| Suite complète backend Docker (`-m "not slow"`) | **520 tests réussis** en 75,36 s |
| Formatage Ruff | 198 fichiers |
| Analyse Ruff | aucune alerte |
| Mypy | 97 fichiers sources, aucune erreur |
| TypeScript frontend (`tsconfig.app.json`) | aucune erreur |
| Validation scientifique | **41/41** cas réussis |
| Empreinte reproductible des résultats | `6973bd97cbbdbd38d64d95dbbedf44bd630e10cacf380a0cc2fda6651ff98e3a` |
| Reproductibilité de l'empreinte | deux exécutions consécutives, empreintes identiques |

Environnement de la campagne : image `deployment/Dockerfile.api` cible
`development`, Python 3.11.15, PostgreSQL/PostGIS 16-3.5 jetable migré par
Alembic jusqu'à `8b1f2d6c4e90`.

## Limites inchangées

- aucune donnée constructeur ni table de jaugeage certifiée n'est chargée ;
- la conformité clause par clause aux référentiels ASME B31.4, API 610, API 650,
  API 2350, ISO 13623 et ISO 7507 n'est pas établie ;
- aucun site pilote n'a été validé par un ingénieur habilité ;
- l'isolation entre organisations reste applicative : aucune politique
  PostgreSQL de sécurité au niveau des lignes n'est en place.
