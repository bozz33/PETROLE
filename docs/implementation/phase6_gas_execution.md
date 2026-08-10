# Phase 6 — Gazoducs et compression

Statut : fondations scientifiques exécutables post-transitoires, non certifiantes.

Base de travail : `main = 6c0ed6aa1632eef0cb207f5ec3bcce9c382a140e`. La branche reste indépendante tant que les gates Phase 4 ne sont pas fermées.

## 1. Références projet

- D07 : modèles thermofluides et limites ;
- D08 : ASME B31.8, ISO 13623 et références compresseurs sélectionnées par projet ;
- D10 : validation scientifique ;
- D17 : Phase 6 — gaz et compression ;
- D20 : pilote gaz futur.

## 2. Sous-lots

1. P6-A — propriétés gaz/composition et enveloppes de validité ;
2. P6-B — conduite gaz stationnaire compressible ;
3. P6-C — line-pack et inventaire ;
4. P6-D — compresseurs centrifuges/alternatifs via cartes fournisseur versionnées ;
5. P6-E — stations, régulation, soutirages/injections ;
6. P6-F — optimisation énergétique sous contraintes ;
7. P6-G — résultats et rapports dédiés gaz ;
8. P6-H — benchmarks indépendants et pilote.

## 3. Fondations déjà codées

- état gaz minimal `p/T/M/Z` avec pression et température absolues ;
- densité issue de l’équation d’état avec `Z` explicitement fourni, sans corrélation implicite ;
- line-pack discret `Σ ρ A Δx` ;
- composition molaire explicite, source obligatoire et somme des fractions vérifiée ;
- masse molaire de mélange `Σ yᵢ Mᵢ` calculée uniquement depuis les composants fournis ;
- cartes compresseur avec provenance/version obligatoires ;
- interpolation à l’intérieur du domaine fourni en débit et vitesse ;
- refus systématique de l’extrapolation hors carte ;
- validation des rendements, ordres de points et lignes de vitesse.

Ces fondations ne constituent pas encore un solveur de gazoduc stationnaire ni une station de compression complète.

## 4. Règles scientifiques

- le fluide gaz est un domaine séparé du moteur liquide ;
- toute équation d’état ou corrélation publie son domaine, sa source et son édition ;
- aucun facteur de compressibilité, efficacité ou limite compresseur n’est inventé ;
- cartes fournisseur brutes conservées et ajustements versionnés ;
- extrapolations hors domaine refusées ou signalées explicitement ;
- line-pack et bilans de masse vérifiables ;
- les modèles stationnaires et transitoires gaz restent explicitement distincts.

## 5. Normes et propriété intellectuelle

Les pages officielles ASME/ISO/API servent à vérifier l’existence, le statut et l’édition. Les clauses contractuelles détaillées ne sont implémentées qu’à partir de copies légalement acquises et revues par l’expert compétent. Aucun texte protégé n’est recopié dans le dépôt.

## 6. Gate avant publication

- propriétés et composition représentatives disponibles ;
- cartes compresseurs réelles ou jeux de référence publics ;
- cas indépendants de validation ;
- revue par un ingénieur gaz/thermofluides ;
- documentation des limites et incertitudes.

## 7. Hors portée

- commande compresseur ;
- SIS/anti-surge opérationnel ;
- certification ASME/API ;
- détection de fuite opérationnelle : Phase 7.
