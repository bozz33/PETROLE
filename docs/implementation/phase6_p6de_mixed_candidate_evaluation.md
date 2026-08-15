# Phase 6 P6-D/P6-E — candidat et évaluation physique mixtes

Statut : `IMPLEMENTED_PHYSICAL_PATH_NO_COUPLED_SOLVER`.

## Objet

Cette brique prolonge le layout structurel du réseau mixte conduites + compresseurs actifs à vitesse imposée. Elle matérialise les inconnues physiques puis évalue un état candidat complet sans lancer de solveur couplé.

Le chemin canonique est :

`unknown state -> candidate physique -> bilan massique équipements + Weymouth conduites + contraintes cartes compresseurs`.

## Inconnues matérialisées

Le candidat reconstruit explicitement :

- les pressions nodales inconnues ;
- les pressions slack imposées ;
- les débits des conduites ;
- les débits des compresseurs actifs ;
- les vitesses compresseurs imposées par le problème ;
- les débits externes slack ;
- les frontières de débit déjà imposées.

Aucune valeur manquante n'est déduite. Le layout est recalculé depuis le problème et doit correspondre exactement au layout fourni.

## Trois familles de résidus

L'évaluation retourne séparément :

1. les résidus de conservation de masse en `kg/s`, en incluant conduites, compresseurs et frontières externes ;
2. les résidus Weymouth des conduites en `Pa²` ;
3. les résidus de rapport de pression des cartes compresseurs en `Pa`.

Ces familles ne sont pas fusionnées ni normalisées dans cette couche.

## Primitive Weymouth conduite seulement

`evaluate_weymouth_pipe_residuals(...)` a été séparée de l'assemblage réseau Weymouth complet. Cette primitive permet au réseau mixte de réutiliser exactement la même loi de conduite sans utiliser par erreur le bilan massique pipe-only, qui ne connaît pas les compresseurs.

## Garde-fous

- couverture exacte des identifiants ;
- aucune extrapolation hors carte compresseur ;
- vitesse compresseur issue du contrôle explicitement fourni ;
- aucun seuil de convergence ;
- aucun `PASS/FAIL` implicite ;
- aucun rendement, puissance, température ou anti-surge inventé ;
- aucun solveur réseau + compresseurs activé dans ce lot.

## Tests

Les tests utilisent uniquement un petit réseau et une carte synthétiques pour vérifier le mécanisme logiciel. Les nombres de test ne sont pas des paramètres de conception ou d'exploitation PETROLE.

## Prochain gate

Avant un solveur couplé, il reste à construire et qualifier :

1. la représentation numérique du problème mixte ;
2. les échelles séparées pour masse, Weymouth et compresseur ;
3. le round-trip `état physique <-> vecteur numérique` ;
4. la fonction pure `x -> r(x)` mixte ;
5. un protocole de convergence et des critères de benchmark pré-enregistrés pour le problème mixte.
