# Phase 7 — P7-E Fusion de preuves explicable

Références : D15, D17 et D20.

## Implémentation

`hydro_leak.evidence_fusion` agrège plusieurs signaux déjà normalisés dans `[0,1]` :

- identifiant détecteur unique ;
- score normalisé ;
- poids strictement positif ;
- provenance obligatoire ;
- contribution individuelle publiée ;
- score global = moyenne pondérée des scores.

Les poids restent visibles et doivent être définis avant l'évaluation sur le jeu de validation lorsqu'ils interviennent dans une campagne de performance.

## Limites

Le score fusionné n'est pas une alarme, n'a aucun seuil implicite et ne déclenche aucune action de procédé. Le module ne choisit ni seuil de suspicion, ni règle de localisation, ni décision opérateur.

Les scores entrants doivent eux-mêmes provenir de détecteurs définis, versionnés et validés. Un score arbitraire injecté en entrée ne devient pas scientifiquement valide parce qu'il est fusionné.

## Gate

La fusion opérationnelle reste bloquée par les données labellisées/essais contrôlés, la pré-définition des métriques et seuils, et la revue indépendante de la campagne Phase 7.
