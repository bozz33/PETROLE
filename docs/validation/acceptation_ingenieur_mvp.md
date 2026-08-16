# Fiche de recette métier — PETROLE MVP 1.0

## Objet

Cette fiche matérialise la revue **humaine** du MVP par l'ingénieur utilisateur de
PETROLE. Dans le périmètre actuel, la plateforme est mono-utilisateur : le même
ingénieur prépare ses études, exécute les calculs, examine les résultats et
consigne sa décision de recette.

Aucun rôle `Approver`, aucune seconde identité et aucune double validation ne
sont requis par le MVP.

Cette fiche ne constitue ni une certification ASME/API/ISO, ni une autorisation
d'exploiter une installation réelle. Une validation indépendante reste
recommandée avant un pilote industriel ou un usage décisionnel sur une
installation réelle.

## Identification

| Champ | Valeur |
|---|---|
| Commit candidat | |
| Tag candidat | |
| URL de l'instance examinée | |
| Date de l'examen | |
| Nom de l'ingénieur utilisateur | |
| Fonction | |
| Domaine de compétence | |
| Référence interne de l'examen | |

## Dossier examiné

Le dossier de référence doit au minimum contenir :

- 101 nœuds et 100 tronçons ;
- 5 stations ;
- 15 pompes ;
- 10 réservoirs ;
- un produit et des références techniques traçables ;
- un scénario nominal ;
- un scénario pompe indisponible ;
- un scénario marche en secours ;
- un scénario débit réduit ;
- un scénario volontairement non réalisable ;
- un transfert bac-à-bac couplé au réseau ;
- une comparaison et une optimisation ;
- une note de calcul et les exports associés.

## Vérifications métier

Cocher uniquement après examen effectif.

- [ ] La topologie représente correctement le réseau de référence.
- [ ] Les équipements sont correctement rattachés aux stations et tronçons.
- [ ] Les hypothèses et unités sont compréhensibles et traçables.
- [ ] Les sources des propriétés produit, pompes, matériaux et règles sont identifiables.
- [ ] Le scénario nominal est physiquement cohérent.
- [ ] Le comportement en pompe indisponible est correctement signalé.
- [ ] Le scénario de secours rétablit le service de manière compréhensible.
- [ ] Le scénario volontairement impossible est refusé ou déclaré non réalisable avec une cause exploitable.
- [ ] Les résultats par tronçon, station et pompe sont suffisants pour une revue d'ingénierie MVP.
- [ ] Les contrôles de pression, NPSH, vitesse et limites projet sont visibles et compréhensibles.
- [ ] Le transfert bac-à-bac présente l'évolution des niveaux, du débit, de la puissance et l'événement de fin.
- [ ] Le bilan matière est compréhensible et sa tolérance est explicitée.
- [ ] La comparaison de scénarios permet d'identifier les écarts importants.
- [ ] L'optimisation publie l'objectif, les contraintes, le solveur, la configuration retenue et le caractère complet ou borné de la recherche.
- [ ] La note de calcul restitue les entrées, méthodes, résultats, avertissements et empreintes attendus.
- [ ] Les exports sont exploitables sans accès direct à la base ou au code.
- [ ] Aucune étape artificielle d'approbation par un second compte n'est nécessaire dans le parcours mono-utilisateur.
- [ ] Les erreurs et non-convergences ne sont pas silencieuses.

## Réserves

| ID | Sévérité | Description | Décision / action requise |
|---|---|---|---|
| | | | |

Sévérités recommandées :

- **S0** : sécurité ou résultat dangereux ; bloque la release ;
- **S1** : erreur scientifique ou fonction métier majeure ; bloque la release ;
- **S2** : défaut important de parcours ou de traçabilité ; à corriger avant acceptation ;
- **S3** : amélioration non bloquante ; peut être planifiée après MVP.

## Décision de recette

Choisir une seule décision :

- [ ] **ACCEPTÉ** — aucune réserve S0/S1/S2 ouverte.
- [ ] **ACCEPTÉ AVEC RÉSERVES NON BLOQUANTES** — uniquement des S3 restent ouvertes.
- [ ] **REFUSÉ** — au moins une réserve S0/S1/S2 reste ouverte.

Commentaire de décision :

>

## Signature

Nom de l'ingénieur utilisateur :
Date :
Signature / validation électronique :

## Traçabilité à archiver avec la fiche

- `summary.json` et `summary.md` produits par `recette_mvp_finale.py` ;
- rapport de qualification final ;
- empreinte de validation scientifique ;
- preuve d'identité du build primaire/secondaire ;
- SBOM CycloneDX ;
- `SHA256SUMS` et signature de release lorsque la clé mainteneur est désignée ;
- note de calcul et exports du projet `REF-MVP-01` ;
- liste des réserves corrigées ou acceptées.
