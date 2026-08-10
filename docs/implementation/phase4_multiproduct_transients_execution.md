# Phase 4 — Multiproduits et transitoires

Statut : contrat d’implémentation post-MVP, non certifiant.

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

## 3. Règles scientifiques

- aucune modification du solveur stationnaire validé pour masquer un écart du solveur transitoire ;
- équations, discrétisation, CFL, tolérances et conditions aux limites publiées ;
- conservation de masse/énergie contrôlée selon le modèle ;
- modèles de cavitation ou colonne séparée uniquement après benchmark dédié ;
- friction instationnaire désactivée tant qu’un modèle et ses références ne sont pas validés ;
- multiproduit et transitoire restent des moteurs explicitement sélectionnés et versionnés.

## 4. Gates

Le lot MOC ne devient publiable qu’après benchmarks analytiques/littérature indépendants et revue d’un spécialiste thermofluides. Un résultat transitoire n’est jamais présenté comme certifié ou comme fonction de protection.

Le multiproduit réel exige des propriétés validées des produits, règles d’interface et cas de référence indépendants.

## 5. Normes

Les textes ASME/API/ISO acquis légalement restent les sources contractuelles. Le logiciel n’embarque que des règles internes synthétiques, versionnées et approuvées ; aucune reproduction de texte protégé.

## 6. Hors portée

- contrôle en boucle fermée ;
- SIS/ESD ;
- gaz : Phase 6 ;
- fuite/RTTM : Phase 7.
