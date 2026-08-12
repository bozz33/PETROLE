# Porte de publication P3-D / P3-E

Référence : `docs/implementation/phase3_analytics_execution.md`, §5.

Le code matérialise sans les modifier les sept conditions déjà définies avant publication pilote des capacités prédictives et conditionnelles :

1. données terrain suffisantes ;
2. horizon métier convenu ;
3. baseline naïve documentée ;
4. protocole train/validation/test figé ;
5. métriques choisies avant observation du test ;
6. seuils conditionnels justifiés et approuvés ;
7. revue ingénieur des variables et limites d’usage.

`AnalyticsPublicationEvidence` associe chaque condition à une preuve, un protocole ou une décision, un instant d’observation et un résultat explicite. `assess_analytics_publication_gate` bloque toute condition absente ou négative et refuse les doublons.

`publishable_for_pilot = true` signifie uniquement que les sept preuves ont été fournies et déclarées positives selon leurs références. Le logiciel ne vérifie pas à lui seul la suffisance réelle des données terrain, la qualité de la revue ingénieur ou la validité métier des seuils. Ce gate ne constitue donc ni une validation industrielle indépendante ni une certification.
