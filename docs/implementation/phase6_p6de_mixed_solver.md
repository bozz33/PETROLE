# Phase 6 P6-D/P6-E — solveur stationnaire conduites + compresseurs actifs

Statut : `IMPLEMENTED_GOVERNED_SOLVER_NOT_BENCHMARKED`.

## Portée

PETROLE dispose désormais d'un premier solveur stationnaire couplé pour :

- conduites évaluées par la formulation Weymouth-SI sélectionnée ;
- compresseurs actifs à vitesse imposée ;
- cartes de performance versionnées ;
- enveloppes de débit fournisseur lorsqu'elles sont disponibles ;
- pressions slack et frontières de débit explicites.

Cette implémentation reste une fondation scientifique post-MVP et ne constitue ni un simulateur industriel qualifié ni une commande procédé.

## Algorithme

Le solveur utilise `scipy.optimize.least_squares` avec la méthode `trf`, comme le solveur P6-B déjà gouverné. Il ne recode aucune équation : chaque évaluation passe par le chemin canonique :

`x -> état physique -> bilan massique + Weymouth + cartes compresseurs -> r(x)`.

Le diagnostic `success` de SciPy est conservé séparément. PETROLE ne retourne `CONVERGED` que lorsque le résidu final satisfait le critère de convergence pré-enregistré et approuvé.

## Entrées obligatoirement approuvées

Le chemin public exige :

- un contexte de qualification exact ;
- un artefact d'échelle `APPROVED` ;
- un artefact d'initialisation `APPROVED` lié au hash exact du layout ;
- un critère de convergence `APPROVED` couvrant les résidus mixtes ;
- une configuration solveur explicitement référencée.

Aucun défaut numérique implicite n'est injecté par le solveur.

## Bornes

Les coordonnées de pression au carré vérifient `p² >= 0`.

Les débits compresseurs sont bornés par :

`domaine carte à vitesse imposée ∩ enveloppe fournisseur disponible`.

Si l'intersection est vide ou dégénérée, le solveur refuse l'exécution. Les conduites et débits slack ne reçoivent pas de borne métier inventée dans cette couche.

## Convergence

Le critère approuvé peut contrôler séparément :

- norme infinie du résidu mis à l'échelle ;
- résidu massique maximal en `kg/s` ;
- résidu Weymouth maximal en `Pa²` ;
- résidu compresseur maximal en `Pa`.

Les seuils des tests sont synthétiques et n'ont aucune valeur industrielle.

## Enveloppes opérationnelles manquantes

Une carte de performance peut permettre un calcul mathématique sans enveloppe opérationnelle séparée. Dans ce cas, le résultat expose explicitement `missing_operational_envelope_compressor_ids`.

Un résultat mathématiquement `CONVERGED` avec cette liste non vide ne doit pas être interprété comme une autorisation d'exploitation ou un point de fonctionnement industriel validé.

## Ce qui reste avant qualification scientifique

1. cas indépendants réseau + compresseurs ;
2. critères de benchmark pré-enregistrés ;
3. comparaison à GasModels ou une autre référence lorsque le type de compresseur/formulation est compatible ;
4. données constructeur réelles ;
5. revue thermofluides ;
6. propriétés gaz représentatives et couplage thermodynamique ;
7. puissance, température de refoulement et limites machine sourcées ;
8. seulement ensuite optimisation/dispatch.

Le solveur ne commande aucun compresseur, aucune vanne et aucun système anti-surge.
