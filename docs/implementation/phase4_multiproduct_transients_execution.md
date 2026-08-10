# Phase 4 — Multiproduits et transitoires

Statut : fondations d’implémentation post-MVP, non certifiantes.

Base de travail : `main = 6c0ed6aa1632eef0cb207f5ec3bcce9c382a140e`. Cette branche reste indépendante des lots V1 jusqu’à intégration contrôlée.

## 1. Références projet

- D07 : référentiel scientifique et mathématique ;
- D08 : ASME B31.4 / ISO 13623 et référentiels applicables ;
- D10 : validation scientifique ;
- D17 : Phase 4 — multiproduits et transitoires ;
- D18 : tests et qualité ;
- D20 : pilote transitoire futur.

## 2. Sous-lots

1. P4-A — modèle de lots/interfaces multiproduits ;
2. P4-B — propriétés dépendantes de la température et mélange contrôlé ;
3. P4-C — solveur transitoire liquide par méthode des caractéristiques (MOC) ;
4. P4-D — vannes, pompes, réservoirs et conditions aux limites transitoires ;
5. P4-E — événements : arrêt pompe, fermeture/ouverture de vanne, changement de consigne hors contrôle-commande ;
6. P4-F — résultats h(x,t), Q(x,t), P(x,t), enveloppes min/max et rapports.

## 3. Fondations déjà codées

### P4-A — lots et interfaces multiproduits

- lots produits avec identifiant, référence produit, volume et provenance obligatoires ;
- séquence ordonnée et immuable de lots ;
- identifiants de lots uniques ;
- interfaces logiques construites entre lots successifs ;
- position de chaque interface dans un axe de volume cumulé injecté ;
- volume total déterministe ;
- aucun volume de mélange/contamination ajouté implicitement.

Cette représentation ne calcule pas encore la position spatiale des interfaces, leur dispersion, leur mélange ou leur évolution thermophysique. Ces phénomènes appartiennent à P4-B et aux futurs modèles de transport multiproduit, avec propriétés validées et benchmarks indépendants.

### P4-C/P4-D — MOC et limites élémentaires

- maillage MOC 1D avec contrôle `CFL = a Δt / Δx = 1` ;
- coefficient caractéristique `B = a/(gA)` ;
- terme de frottement quasi-stationnaire explicite ;
- intersection des caractéristiques C+ / C- aux nœuds intérieurs ;
- conditions aux limites à charge imposée aux extrémités ;
- conditions aux limites à débit imposé aux extrémités ;
- solveur de référence pour une conduite uniforme à charges fixes ;
- snapshots `H(x,t)` et `Q(x,t)` à chaque pas ;
- tests de maintien d’un état uniforme et propagation discrète CFL=1.

La condition de débit imposé est une brique mathématique. Elle ne prétend pas modéliser à elle seule la loi d’une vanne, une pompe en roue libre ou un système de protection. Ces équipements exigent leurs propres relations, paramètres et benchmarks.

## 4. Règles scientifiques

- aucune modification du solveur stationnaire validé pour masquer un écart du solveur transitoire ;
- équations, discrétisation, CFL, tolérances et conditions aux limites publiées ;
- conservation de masse/énergie contrôlée selon le modèle ;
- modèles de cavitation ou colonne séparée uniquement après benchmark dédié ;
- friction instationnaire désactivée tant qu’un modèle et ses références ne sont pas validés ;
- multiproduit et transitoire restent des moteurs explicitement sélectionnés et versionnés ;
- aucune largeur d’interface, dispersion ou contamination n’est inventée sans modèle sourcé et validé.

## 5. Gates

Le lot MOC ne devient publiable qu’après benchmarks analytiques/littérature indépendants et revue d’un spécialiste thermofluides. Un résultat transitoire n’est jamais présenté comme certifié ou comme fonction de protection.

Le multiproduit réel exige des propriétés validées des produits, règles d’interface et cas de référence indépendants.

## 6. Normes

Les textes ASME/API/ISO acquis légalement restent les sources contractuelles. Le logiciel n’embarque que des règles internes synthétiques, versionnées et approuvées ; aucune reproduction de texte protégé.

## 7. Hors portée

- contrôle en boucle fermée ;
- SIS/ESD ;
- gaz : Phase 6 ;
- fuite/RTTM : Phase 7.
