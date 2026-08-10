# V1-D — Résultats ingénieur avancés D19

Statut : contrat d’implémentation Phase 2 / Pilote-V1. Aucun effet de certification.

Base documentaire : D04 FR-LIQ-003, FR-LIQ-005, FR-LIQ-007 et D19 §§5, 10, 15.

Base logicielle : `main` à `6c0ed6aa1632eef0cb207f5ec3bcce9c382a140e`.

## 1. Objet

Compléter la restitution hydraulique existante sans modifier le moteur HydroLiquid : rendre visibles, sur les profils et graphiques de résultats, les stations, limites de pression et zones déjà calculées ou configurées par le modèle.

Le lot reste analytique. Il ne calcule aucune résistance réglementaire nouvelle, ne remplace pas une vérification d’intégrité mécanique et ne transforme pas une MAOP/MAWP fournie par le modèle en certification de ligne.

## 2. État de départ

Le MVP fournit déjà :

- profil terrain + ligne piézométrique ;
- pression absolue et vitesse suivant le chaînage ;
- résultats détaillés par tronçon avec marge MAOP ;
- résultats station aspiration/refoulement ;
- courbes pompes, rendement, puissance et NPSH ;
- marqueurs calculés `below_vapor_pressure` et `gravity_zone` sur les points de profil ;
- MAOP/MAWP par tronçon via les résultats détaillés.

V1-D complète la présentation et le contrat d’export, pas les équations du solveur.

## 3. Cible fonctionnelle V1-D1

### 3.1 Profil hydraulique enrichi

Afficher sur un même profil :

- terrain ;
- ligne piézométrique ;
- repères de stations au chaînage réellement calculé ;
- annotation des sauts de charge aux stations quand ils sont présents dans les résultats ;
- zones gravitaires uniquement lorsque le solveur les signale et que le mode correspondant est actif ;
- légende et unités visibles sans dépendre uniquement de la couleur.

### 3.2 Pression et enveloppes opératoires

Afficher suivant le chaînage :

- pression calculée ;
- limite MAOP/MAWP du tronçon, issue des données du modèle ;
- seuil de pression vapeur uniquement lorsqu’une valeur physique traçable est disponible pour le produit/scénario ;
- localisation des points sous pression vapeur ;
- marges minimales et maximales disponibles par tronçon ;
- stations et changements de tronçon.

Aucune formule générique de résistance de conduite n’est introduite dans ce lot. Une future vérification d’intégrité mécanique reste un domaine distinct.

### 3.3 Diagnostics ingénieur

Fournir une synthèse dérivée des résultats existants :

- pression minimale, localisation et marge au seuil pertinent ;
- pression maximale, localisation et marge MAOP/MAWP ;
- nombre de points `below_vapor_pressure` ;
- nombre/étendue des zones gravitaires signalées ;
- stations traversées et états ;
- liens vers les tableaux détaillés tronçons/stations.

Les diagnostics doivent conserver le caractère calculé, configuré ou indisponible de chaque limite. Une limite absente n’est jamais remplacée par une valeur arbitraire.

## 4. Contrat de données

Le frontend consomme en priorité les sorties déjà persistées :

- `CalculationPayload.profile` ;
- `CalculationPayload.segments` ;
- `CalculationPayload.stations` ;
- données produit/scénario nécessaires au seuil vapeur si elles sont déjà publiées dans le résultat ou dans une ressource versionnée liée au calcul.

Si une information D19 nécessaire n’est pas suffisamment publiée par l’API, l’API peut ajouter une vue de restitution dérivée et déterministe. Elle ne doit pas recalculer la physique avec une seconde implémentation concurrente du moteur.

Chaque valeur d’enveloppe doit être rattachable à sa source : résultat du calcul, donnée de tronçon, propriété produit ou indisponible.

## 5. Export image

V1-D doit fournir un export autonome des graphiques d’ingénierie au minimum en PNG haute résolution :

- profil hydraulique enrichi ;
- pression et enveloppes opératoires.

L’image doit inclure titre, calcul/scénario, axes, unités, légende et date/identifiant de génération. L’export ne constitue pas à lui seul un rapport approuvé ; les rapports restent traités par V1-E.

## 6. Cas COURSEWORK-460KM-01

Le cas pédagogique multi-stations peut être utilisé comme régression visuelle pour vérifier :

- grand nombre de stations ;
- annotations sans chevauchement majeur ;
- sauts de charge visibles ;
- continuité du chaînage ;
- lisibilité bureau et mobile ;
- export PNG.

Il reste explicitement un cas pédagogique/régression. Il ne constitue ni validation prédictive terrain ni certification.

## 7. Critères d’acceptation

V1-D1 est techniquement fermé lorsque :

1. les graphiques de base MVP restent inchangés scientifiquement ;
2. les stations sont positionnées à partir des résultats, sans chaînage inventé ;
3. la MAOP/MAWP est affichée par tronçon à partir des données versionnées ;
4. le seuil vapeur n’est affiché que si sa provenance est traçable ;
5. les zones gravitaires ne sont affichées que lorsque le résultat les signale ;
6. aucune limite absente n’est remplacée par une constante implicite ;
7. les marges affichées sont cohérentes avec les tables détaillées ;
8. l’export PNG est lisible et contient les métadonnées minimales ;
9. tests Vitest et Playwright couvrent bureau/mobile et une ligne multi-stations ;
10. backend/science existants, TypeScript, Playwright, CodeQL, images et migrations restent verts.

## 8. Hors portée

- calcul réglementaire de résistance de conduite ;
- corrosion, fitness-for-service ou RBI ;
- transitoires/coups de bélier ;
- multiproduit thermique ;
- SCADA/historian ;
- commande temps réel ;
- calibration ;
- seuils industriels arbitraires ;
- certification.

## 9. Dépendances avec les autres lots

V1-D est volontairement indépendant de V1-A/V1-B et peut être développé sur une branche issue du candidat MVP. Après la cérémonie `v1.0.0-mvp`, les branches Phase 2 seront intégrées dans l’ordre décidé par l’équipe, avec rebase/retarget de V1-D sur la nouvelle baseline V1 avant fusion.

V1-E utilisera ensuite les graphiques et diagnostics V1-D pour RPT-07/RPT-08 et les exports de résultats applicables.