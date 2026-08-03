# Recette locale du backend MVP

- Date d'exécution : 3 août 2026
- Environnement : Docker Desktop, image API Python 3.11
- Référence : documentation maître v2.0, critères § 12.1 et § 15.2
- Portée : backend, moteurs scientifiques, base, stockage et exploitation locale

## Résultat

Les portes backend automatisables exécutées sont franchies localement. La qualification
détaillée, ses limites et la matrice des scénarios se trouvent dans
`docs/validation/qualification_backend_mvp.md`. La validation utilisateur par un ingénieur
métier, le TLS du serveur cible et le déploiement public restent externes au dépôt. La CI
distante n'a pas été utilisée, le quota GitHub Actions du compte étant indisponible ; les
commandes équivalentes ont été exécutées sur la pile Docker locale.

## Qualité du code

| Contrôle | Commande | Résultat |
|---|---|---:|
| Format | `python -m ruff format --check apps packages tests` | Réussi |
| Analyse statique | `python -m ruff check apps packages tests` | Réussi |
| Typage | `python -m mypy packages apps/api` | 91 fichiers, aucune erreur |
| Tests hôte sans benchmarks lents | `pytest -m "not slow" --cov=...` | 470 réussis, 1 optionnel ignoré, couverture 83 % |
| Benchmarks hôte lents | `pytest -m slow` | 3 réussis |
| Tests Docker | `pytest -q` | 482 réussis, pandapipes inclus |

Le test optionnel ignoré sur l'hôte correspond uniquement à pandapipes, absent du virtualenv
Windows. Il est exécuté dans l'image Docker de développement qui embarque la version 0.14.0.

## Validation scientifique

La commande `hydro-validate` a réussi 41 cas : portes `V-001` à `V-020`, cas analytiques et
sept références externes STANET, OpenModelica et DWSIM. L'empreinte de la preuve locale est :

`f77b96061174cadf0a647b75d49c42c99caca9e476514dd95d4e115c7f5d50b1`

La preuve de concept POC-OS-04 exécute neuf contrôles pandapipes : cohérence horizontale,
dénivelé, pertes singulières, pression absolue, cas incompatibles, entrée invalide,
non-convergence structurée et verrou d'approbation.

## Capacité et performance

Les durées ci-dessous sont les durées d'appel publiées par pytest dans l'image Docker. Les
seuils sont ceux de la documentation maître § 12.1.

| Cas | Charge | Mesure locale | Cible MVP | Verdict |
|---|---:|---:|---:|---:|
| Simulation de capacité P95 | 20 × 1 000 tronçons | 0,320 s | < 10 s | Réussi |
| Simulation étendue | 10 000 tronçons | 105,860 s ; 19,639 Mio | Mesure D18 | Réussi |
| Configurations | 100 simulations | 0,960 s | < 120 s | Réussi |
| Charge API | 25 utilisateurs, 500 requêtes | P95 0,603 s, 0 erreur | < 2 s | Réussi |
| Import | 1 000 000 lignes | 120,318 s ; 465,008 Mio | Mesure D18 | Réussi |
| Rapport volumineux | 1 000 tronçons, 30 pages | 2,360 s ; 190 576 octets | < 60 s | Réussi |
| Optimisation bornée | 65 535 configurations évaluées | Porte automatisée | < 300 s | Réussi |

Les tests sont conservés dans `tests/performance/test_mvp_capacity.py` et dans le test API de
comparaison. Les seuils font partie de la campagne locale normale afin de détecter une
régression de complexité.

## Sauvegarde et restauration

L'exercice local a couvert PostgreSQL, les migrations Alembic et le volume MinIO :

1. création d'un dump PostgreSQL au format personnalisé ;
2. contrôle du dump avec `pg_restore --list` ;
3. création et lecture de l'archive du stockage objet ;
4. production d'un manifeste SHA-256 ;
5. contrôle des empreintes avant restauration ;
6. remplacement de la base et du stockage par la sauvegarde vérifiée ;
7. application des migrations restantes et redémarrage des services ;
8. contrôle final de l'API, de PostgreSQL et de MinIO.

La restauration a terminé en 45 secondes, très en deçà du RTO MVP de huit heures. La base a
retrouvé la révision Alembic `4d7f9a3b2c85 (head)` et l'endpoint de disponibilité a retourné
`database=ready` et `object_storage=ready`.

## Limites de cette recette

- Les mesures décrivent cette machine locale ; elles doivent être rejouées sur l'infrastructure
  de recette avant mise en production.
- La fréquence quotidienne de sauvegarde doit être configurée par l'exploitant pour tenir le RPO
  de 24 heures.
- La validation métier finale exige un ingénieur habilité et des données industrielles autorisées.
- Le TLS, les secrets de production et la supervision externe dépendent de l'environnement cible.
- Le scan Trivy et le DAST OWASP ZAP restent non conclus, leurs téléchargements externes ayant
  dépassé cinq minutes.
- Les scénarios partiels ou absents sont recensés dans la qualification détaillée ; ils ne sont
  pas assimilés à des tests réussis.
