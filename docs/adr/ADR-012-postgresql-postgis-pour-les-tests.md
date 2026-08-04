# ADR-012 — PostgreSQL/PostGIS comme unique base des tests de persistance

- **Statut :** accepté
- **Date :** 2026-08-04
- **Décision :** infrastructure de test et parité avec la production

## Contexte

PETROLE dépend de comportements propres à PostgreSQL/PostGIS : JSON/JSONB strict, contraintes, transactions, concurrence du worker, verrouillage, migrations Alembic et types géographiques. Une base embarquée permissive avait masqué un défaut de persistance qui apparaissait dans l'environnement réel.

## Décision

1. PostgreSQL/PostGIS est l'unique moteur autorisé pour les tests nécessitant une persistance.
2. Les tests scientifiques et de domaine purs n'utilisent aucune base.
3. La base d'intégration est jetable, distincte de tout environnement applicatif, stockée en mémoire volatile et son nom se termine obligatoirement par `_test`.
4. `HYDRO_TEST_DATABASE_URL` est obligatoire. Aucun repli vers une URL de développement, recette ou production n'est autorisé.
5. Le schéma est créé et mis à niveau exclusivement par `alembic upgrade head`. `metadata.create_all()` et `metadata.drop_all()` sont interdits dans les tests.
6. Les tests API ordinaires sont isolés par une transaction externe SQLAlchemy. Chaque requête ouvre sa propre session et utilise `join_transaction_mode="create_savepoint"`; la transaction externe est annulée après le test.
7. Les scénarios multi-connexion, notamment le worker, utilisent de vrais commits et des sessions indépendantes. La base dédiée est remise à zéro par un composant d'infrastructure centralisé, jamais par du SQL écrit dans un fichier de test.
8. Les chaînes SQL brutes, `text()` et la création locale de moteurs sont interdites dans `tests/`.
9. Un analyseur AST fait échouer la qualification si une violation est réintroduite.
10. La version de PostgreSQL/PostGIS du compose de test suit la version majeure de l'environnement cible et doit être épinglée avant la livraison de production.

## Séquence de qualification

1. démarrage de PostgreSQL/PostGIS ;
2. attente du healthcheck ;
3. application des migrations Alembic ;
4. vérification de la révision courante ;
5. exécution des tests ;
6. destruction des conteneurs et volumes jetables.

## Conséquences

- Les tests reproduisent les contraintes de la production.
- Les erreurs liées à JSONB, aux transactions et au worker sont détectées avant la recette.
- La suite nécessite Docker et PostgreSQL/PostGIS pour les tests d'intégration.
- Les tests unitaires restent rapides parce qu'ils ne chargent aucune base.
- Une base mal nommée ou non migrée provoque un arrêt immédiat de la suite.

## Implémentation de référence

- `deployment/docker-compose.test.yml`
- `tests/conftest.py`
- `packages/shared/hydro_shared/testing/postgres.py`
- `deployment/scripts/check_test_database_policy.py`

## Références officielles

- SQLAlchemy 2 — transactions externes et `join_transaction_mode` : https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
- Alembic — migrations et commandes : https://alembic.sqlalchemy.org/en/latest/
- Docker Compose — ordre de démarrage et conditions : https://docs.docker.com/compose/how-tos/startup-order/
- PostgreSQL — types JSON : https://www.postgresql.org/docs/current/datatype-json.html
- PostGIS : https://postgis.net/documentation/
