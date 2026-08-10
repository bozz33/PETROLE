# Phase 4 — P4-E Conditions aux limites temporelles programmées

Référence principale : D07 §11, complétée par D10/D17.

## Implémentation

`hydro_transients.events` ajoute des programmes temporels explicitement fournis pour les conditions aux limites MOC déjà disponibles :

- type `head` ou `flow` ;
- points `(temps, valeur)` strictement croissants à partir de `t=0` ;
- interpolation `step` ou `linear` explicitement choisie ;
- provenance obligatoire ;
- aucune extrapolation après le dernier point ;
- solveur `simulate_scheduled_boundary_pipe` qui applique le programme à chaque pas MOC.

## Usage

Cette brique permet de reproduire des scénarios imposés de variation de charge ou débit et de vérifier la réponse du schéma MOC. Elle peut servir de fondation aux futurs modèles de fermeture de vanne, arrêt pompe ou changement de réservoir.

## Limite critique

Un programme de débit ou de charge n'est **pas** une loi physique de vanne ou de pompe. PETROLE ne doit pas présenter un simple signal imposé comme simulation d'un équipement tant que sa relation constitutive, ses paramètres et ses benchmarks n'ont pas été sélectionnés dans D07/D10.

Aucune commande réelle n'est émise ; les programmes sont des entrées de simulation hors ligne.
