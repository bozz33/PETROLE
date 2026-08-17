# Phase 6 P6-D — thermodynamique et puissance compresseur

Statut : `IMPLEMENTED_FOUNDATIONS_NOT_INDUSTRIALLY_QUALIFIED`.

## Objectif

Cette brique ajoute les calculs thermodynamiques nécessaires à la future puissance et température de refoulement sans inventer de propriété, de rendement ou de limite machine.

Deux couches restent séparées :

1. bilan d'énergie stationnaire avec toutes les contributions explicitement fournies ;
2. fermeture isentropique et méthode de propriétés.

## Bilan d'énergie stationnaire

`evaluate_steady_compressor_energy_balance(...)` consomme explicitement :

- débit massique ;
- enthalpie entrée/sortie ;
- énergie cinétique spécifique entrée/sortie ;
- énergie potentielle spécifique entrée/sortie ;
- flux thermique vers le gaz ;
- référence de l'état ;
- référence de l'équation.

Convention du module :

- chaleur positive vers le gaz ;
- puissance mécanique positive vers le volume de contrôle compresseur.

Aucun terme n'est mis à zéro implicitement. Si un projet veut négliger chaleur, énergie cinétique ou potentielle, cette hypothèse doit être matérialisée par des valeurs explicites et une provenance/justification amont.

## Fermeture isentropique

`evaluate_isentropic_compressor_enthalpy_closure(...)` reçoit :

- `h1` ;
- `h2s` ;
- rendement isentropique ;
- source des propriétés ;
- source du rendement ;
- référence de l'équation.

Le rendement peut être lié directement à un `CompressorOperatingPoint` issu d'une carte versionnée via `build_isentropic_closure_from_map(...)`.

La fermeture ne recherche aucune propriété thermodynamique elle-même.

## Adaptateur CoolProp

`evaluate_coolprop_compressor_states(...)` réalise une première fermeture de propriétés pour un fluide CoolProp explicitement nommé :

- `h1` et `s1` depuis `P1,T1` ;
- `h2s` et `T2s` à `P2,s1` ;
- `h2` à partir du rendement isentropique fourni ;
- `T2` depuis `P2,h2` ;
- version CoolProp réellement utilisée conservée dans le résultat.

Cette version n'invente aucune composition de gaz naturel. Le nom de fluide exact et sa provenance sont des entrées obligatoires.

## Limites actuelles

Ne sont pas encore qualifiés dans cette brique :

- mélanges gaz naturel réels ;
- EOS/méthode de mélange retenue par projet ;
- refroidisseurs inter-étages ;
- multi-étagement ;
- pertes mécaniques ;
- rendement moteur/turbine ;
- puissance auxiliaire ;
- température ou puissance maximale constructeur ;
- anti-surge opérationnel.

## Gate suivant

Le prochain développement peut joindre, en post-traitement :

`résultat réseau mixte + température d'aspiration sourcée + fluide/méthode propriétés + rendement de carte -> h/T sortie + puissance thermodynamique`.

Cette étape devra conserver explicitement les hypothèses énergétiques et refuser tout point hors domaine de propriétés ou hors carte/enveloppe.
