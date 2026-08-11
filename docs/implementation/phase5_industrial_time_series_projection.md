# P5-F — Projection des sources industrielles vers les séries existantes

Références : D15 §6 à §9, D12 séries temporelles, contrat Phase 5.

## Décision de modèle

Les mesures OPC UA/historian utilisent les mêmes objets métier que les imports historiques : `tags`, `samples_raw`, `samples_normalized` et `time_series_imports`. Elles ne créent pas un second modèle temporel et ne fabriquent pas un faux dataset fichier.

La migration `d8f1a6c3e590` rend `dataset_id` optionnel pour une ingestion industrielle. Les imports fichiers conservent leur filiation `dataset_id` existante. Un index partiel rend la clé de batch industriel unique par tag et un index unique `(time_series_import_id, sequence_number)` protège l'idempotence du replay.

Le downgrade refuse explicitement de revenir au schéma précédent si des séries industrielles sans dataset existent ; aucune donnée n'est supprimée silencieusement pour satisfaire un rollback.

## Ordre de traitement

`ingest_industrial_batch` :

1. valide la clé d'idempotence, la version de traitement, le hash SHA-256 de source et les séquences ;
2. verrouille et vérifie le tag existant ;
3. crée un journal `time_series_imports` avec `dataset_id = NULL` ;
4. conserve chaque échantillon dans `samples_raw`, avec valeur/unité/qualité, SourceTimestamp, ServerTimestamp, payload source et référence du mapping qualité ;
5. vérifie que l'unité reçue correspond à l'unité approuvée du tag ;
6. convertit les valeurs numériques finies en SI avec le moteur d'unités PETROLE ;
7. crée `samples_normalized` avec `processing_version` et lignage industriel ;
8. conserve les valeurs non projetables uniquement en brut et les déclare comme rejets de projection ;
9. retourne le journal existant lors du replay du même batch.

Une qualité `bad` n'est pas effacée : si la valeur est numérique et dimensionnellement valide, sa projection SI conserve `quality = bad`. Les couches analytiques existantes restent responsables de l'exclure de leurs KPI selon leur politique explicite.

## Limites

Cette brique ne crée aucune session OPC UA, ne lit aucun historian et n'écrit dans aucun système industriel. Le producteur du batch reste P5-B/P5-C/P5-H. Le passage de cette brique en CI ne constitue ni une qualification OT-4/OT-5, ni une certification industrielle.
