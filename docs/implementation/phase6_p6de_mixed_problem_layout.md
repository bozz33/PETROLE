# Phase 6 — P6-D/P6-E — layout du problème stationnaire mixte

## Portée

Ce lot définit le système d'inconnues et d'équations d'un réseau contenant :

- conduites stationnaires Weymouth ;
- compresseurs **actifs** ;
- vitesse de chaque compresseur imposée et sourcée ;
- carte fournisseur versionnée liée explicitement à chaque compresseur ;
- un slack de pression par composante connexe ;
- injections et soutirages imposés.

Aucune résolution numérique n'est réalisée par cette couche.

## Connectivité

La connectivité est calculée sur le graphe physique combiné :

- chaque conduite relie ses deux noeuds ;
- chaque compresseur actif relie ses noeuds amont et aval.

Un compresseur fait donc partie de la détermination des composantes connexes. Chaque composante doit posséder exactement un slack de pression.

## Comptage structurel

Pour `N` noeuds, `E` conduites, `C` compresseurs actifs et `K` composantes connexes :

### Inconnues

- `N-K` pressions nodales ;
- `E` débits de conduites ;
- `C` débits compresseurs ;
- `K` débits externes des noeuds slack.

Total : `N + E + C`.

### Équations

- `N` bilans de masse ;
- `E` équations constitutives de conduites ;
- `C` contraintes de cartes compresseurs.

Total : `N + E + C`.

Le layout est donc structurellement carré sans suppression arbitraire d'un bilan nodal.

## Contrôles fermés

Le constructeur refuse :

- identifiants compresseurs dupliqués ;
- contrôles de vitesse manquants ou surnuméraires ;
- bindings de cartes manquants ou surnuméraires ;
- frontières sur des noeuds inconnus ;
- slack sur un noeud inconnu ;
- zéro ou plusieurs slacks dans une même composante connexe ;
- compresseur reliant un noeud absent du réseau.

## Limites

Le layout ne prend actuellement en charge que les compresseurs actifs à vitesse imposée. Les modes arrêt, bypass, recyclage et régulation ne sont pas transformés en équations implicites. Ils devront être représentés par des modes d'équipement explicitement définis avant extension du solveur.

Ce lot ne crée aucun solveur réseau mixte et ne modifie pas le solveur Weymouth P6-B existant.
