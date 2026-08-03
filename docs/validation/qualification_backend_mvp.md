# Qualification locale du backend MVP

- Date : 3 août 2026
- Environnement principal : Windows, Python 3.13, Docker Desktop et image API Python 3.11
- Référence fonctionnelle : D04, D05, D06, D10, D18 et D20
- Portée : API, persistance, worker, stockage objet, calculs liquides, transferts,
  optimisation, rapports et exploitation locale

## Verdict

Le backend franchit les portes automatisées exécutées localement. Il n'est cependant pas
qualifiable à 100 % pour un usage industriel : le DAST OWASP ZAP et le scan d'image Trivy
n'ont pas pu télécharger leurs bases ou images, plusieurs scénarios avancés du catalogue sont
partiels, et la validation normative et industrielle exige des textes sous licence, des données
d'opérateur et l'approbation d'un ingénieur habilité.

Cette distinction est obligatoire : un test logiciel réussi ne constitue ni une certification
ASME/API/ISO, ni une autorisation d'exploitation.

## Campagne automatisée

| Porte | Résultat |
|---|---:|
| Ruff format et analyse statique | Réussi |
| mypy | 91 fichiers, aucune erreur |
| Tests hôte sans instrumentation lente | 470 réussis, 1 optionnel ignoré |
| Benchmarks hôte lents | 3 réussis |
| Couverture hôte | 83 % |
| Tests Docker Linux | 482 réussis |
| Cas scientifiques | 41/41 réussis |
| Empreinte de la preuve scientifique | `f77b96061174cadf0a647b75d49c42c99caca9e476514dd95d4e115c7f5d50b1` |

Le test ignoré sur l'hôte Windows correspond au module pandapipes non installé dans ce
virtualenv. Il est inclus et réussi dans la campagne Docker avec pandapipes 0.14.0.

## Benchmarks scientifiques externes

Les valeurs tierces sont figées dans
`datasets/reference_cases/external_benchmarks_v1.json`, avec URL, version, méthode, date de
consultation et empreinte de la source. Les cas pandapipes proviennent des réseaux officiels
`water_one_pipe1`, `water_one_pipe2` et `water_one_pipe3`, eux-mêmes accompagnés des résultats
STANET et OpenModelica publiés par le projet. Le cas pompe provient du rapport officiel de
validation DWSIM du 3 mai 2026.

| Cas | Plus grand écart relatif | Tolérance | Verdict |
|---|---:|---:|---:|
| STANET, one_pipe1 | 24,889181 % | 30 % | Comparaison de classe B réussie |
| OpenModelica, one_pipe1 | 0,039591 % | 0,2 % | Réussi |
| STANET, one_pipe2 | 0,007864 % | 0,2 % | Réussi |
| OpenModelica, one_pipe2 | 0,039573 % | 0,2 % | Réussi |
| STANET, one_pipe3 | 0,014240 % | 0,2 % | Réussi |
| OpenModelica, one_pipe3 | 0,050559 % | 0,2 % | Réussi |
| DWSIM U03, pompe eau, 1 kg/s et 10 bar | 0,000028 % | 5 % | Réussi |

Le premier cas STANET se situe vers `Re = 2 630`. STANET applique directement la loi
turbulente Prandtl-Colebrook, tandis que HydroLiquid interpole entre les régimes laminaire et
turbulent. L'écart est donc expliqué et conservé ; ce cas ne prouve pas une équivalence fine
des deux modèles dans la zone de transition.

## Performance et capacité

| Essai | Résultat local | Cible ou statut |
|---|---:|---:|
| P95 de 20 calculs, 1 000 tronçons | 0,320133 s | < 10 s, réussi |
| Réseau de 10 000 tronçons | 105,859863 s ; 19,639 Mio | mesure D18, réussi |
| 100 configurations simples | 0,959817 s | < 120 s, réussi |
| Rapport de 1 000 tronçons | 2,360494 s ; 190 576 octets ; 30 pages | < 60 s et < 25 Mo, réussi |
| 25 utilisateurs, 500 requêtes | P95 0,602872 s ; 0 erreur | < 2 s, réussi |
| Import réel de 1 000 000 lignes | 120,318165 s ; 465,008 Mio | réussi |
| Rejeu de l'import par idempotence | 0,001975 s | réussi |
| Optimisation exhaustive | 65 535 configurations | < 300 s, réussi |

Les mesures dépendent de la machine. Elles doivent être rejouées sur l'infrastructure de
recette avant toute promesse contractuelle de débit ou de temps de réponse.

## Robustesse et reprise

| Essai | Résultat |
|---|---|
| 100 entrées publiques invalides ou non physiques | 100 diagnostics attendus, aucun état valide altéré |
| Déterminisme | 10 répétitions scientifiquement identiques |
| Concurrence worker | 8 prétendants, exactement 1 prise de job |
| Reprise d'un job périmé | 1 job récupéré puis repris |
| Migration | base vide → head → base → head, puis `alembic check` sans écart |
| PostgreSQL arrêté | disponibilité HTTP `503`, base déclarée indisponible |
| MinIO arrêté | `503` structuré en 0,733 s, stockage déclaré indisponible |
| Retour MinIO | disponibilité `200` après redémarrage |
| Sauvegarde/restauration réelle | révision `4d7f9a3b2c85 (head)`, restauration réussie en 45 s |

L'import million utilise désormais des écritures PostgreSQL par lots de 5 000 lignes. Son
empreinte incrémentale est couverte par un test d'équivalence avec la sérialisation canonique.

## Sécurité et chaîne de dépendances

| Contrôle | Résultat |
|---|---:|
| Bandit, sources Python | 0 alerte |
| pip-audit, environnement Python | 101 dépendances, 0 vulnérabilité connue |
| npm audit | 163 dépendances, 0 vulnérabilité connue |
| Gitleaks, 12 commits | 0 secret après qualification d'une fausse positive exacte |
| SBOM CycloneDX Python | 101 composants |
| SBOM CycloneDX web | 111 composants |
| Inventaire de licences | produit pour Python et le web |
| `pip check` hôte et Docker | aucune dépendance cassée |
| Trivy, image et configuration | non conclu : téléchargement de base bloqué après 5 min |
| OWASP ZAP DAST | non exécuté : téléchargement de l'image GHCR bloqué après 5 min |
| Pentest externe et revue OT | requis avant pilote industriel |

Les artefacts détaillés sont conservés localement dans `var/validation`. Ce répertoire est
ignoré par Git, car il contient des résultats propres à la machine et à l'instant d'exécution.

## Couverture des cas d'usage MVP

| Cas | Couverture backend constatée |
|---|---|
| UC-001 projet et référentiel | API, versionnement, sites, isolement et audit testés |
| UC-002 profil et réseau | CSV/XLSX, graphe, validation, clonage et compilation testés |
| UC-003 produit | catalogue versionné et propriétés testés |
| UC-004 courbe de pompe | import métier, validation et réutilisation testés |
| UC-005 régime hydraulique | marche directe, résolution et diagnostics testés |
| UC-006 série/parallèle | combinaisons et partage de débit testés |
| UC-007 pompe indisponible/secours | états, substitution et baseline immuable testés |
| UC-008 comparaison des modes | comparaison persistée et optimisation testées |
| UC-009 réservoir et barémage | création, monotonie, inversion et niveaux testés |
| UC-010 transfert bac-à-bac | dynamique, limites, énergie et bilan testés |
| UC-011 bilan matière | écarts et incertitudes testés |
| UC-012 note de calcul | PDF déterministe, traçable et volumineux testé |
| UC-013 historiques CSV/Excel | lignage, erreurs, million de lignes et idempotence testés |

## Couverture des scénarios d'exploitation

La mention « partiel » signifie que le calcul disponible a été testé, mais qu'une sortie
annoncée par D06 manque encore.

| Scénario | État vérifié |
|---|---|
| SC-L-01 fonctionnement normal | Couvert |
| SC-L-02 pompe arrêtée | Couvert |
| SC-L-03 secours activé | Couvert |
| SC-L-04 station contournée | Couvert |
| SC-L-05 perte totale d'une station | Partiel : faisabilité stationnaire, pas de temps avant contrainte |
| SC-L-06 filtre colmaté | Couvert par augmentation des pertes singulières |
| SC-L-07 vanne partiellement fermée | Couvert |
| SC-L-08 soutirage intermédiaire | Couvert avec conservation de masse |
| SC-L-09 température basse | Partiel : viscosité dépendante de la température, pas de modèle thermique |
| SC-L-10 cavitation | Couvert par pression de vapeur et marge NPSH |
| SC-L-11 zone gravitaire | Partiel : dépression localisée, pas de degré de remplissage diphasique |
| SC-L-12 limite de pression | Couvert tronçon par tronçon |
| SC-T-01 transfert normal | Couvert |
| SC-T-02 niveau haut | Couvert avec interpolation de l'instant d'arrêt |
| SC-T-03 pompe indisponible | Partiel : contrainte hydraulique, pas de recherche de pompe alternative |
| SC-T-04 mauvais alignement de vannes | Non couvert par le moteur de transfert |
| SC-T-05 produit incompatible | Couvert et bloquant |
| SC-T-06 écart de bilan matière | Couvert avec incertitudes |
| SC-T-07 réception et expédition simultanées | Non couvert ; planification multi-mouvements classée LATER |
| SC-T-08 viscosité élevée | Partiel : point hydraulique injectable, pas de décision de chauffage |
| SC-T-09 débitmètre indisponible | Non couvert automatiquement |
| SC-T-10 évent ou soupape indisponible | Non couvert par le modèle actuel |

## Conclusion de livraison

Les moteurs, l'API et l'exploitation locale sont fortement testés et reproductibles. La formule
« tous les problèmes possibles » n'est pas démontrable pour un logiciel ouvert à des données
arbitraires. La preuve fournie porte sur le catalogue fini ci-dessus, 100 invalidités construites,
les tests de propriétés et les pannes réelles de dépendances.

Le backend ne doit donc pas être déclaré « livré industriel à 100 % » tant que les éléments
suivants ne sont pas fermés : DAST, scan d'image, scénarios partiels requis par le pilote,
validation clause par clause des règles normatives, données réelles anonymisées, revue métier,
pentest et essai sur l'infrastructure cible.
