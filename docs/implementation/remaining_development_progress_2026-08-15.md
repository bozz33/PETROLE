# PETROLE — avancement développement restant — 2026-08-15

Ce journal complète `remaining_development_master_plan.md`. Il distingue volontairement code implémenté, checkpoint CI qualifié et travail encore soumis aux gates.

## Checkpoint confirmé full-green avant les lots récents

Le head `ae71ef122854d7a5993b3c2c4662c9df13af3f9b` a franchi :

- Ruff format ;
- Ruff lint ;
- mypy ;
- PostgreSQL/PostGIS de test ;
- migrations ;
- pytest + couverture ;
- couverture globale et noyau scientifique ;
- dossier de validation ;
- TypeScript/build/audit/Playwright ;
- images de production ;
- migrations production ;
- schema drift ;
- CodeQL ;
- référence GasModels P6-H.

Ce checkpoint contient le premier solveur stationnaire couplé conduites Weymouth + compresseurs actifs à vitesse imposée, gouverné par des artefacts et critères `APPROVED`.

## Lots ajoutés après ce checkpoint

### P6-G — restitution mixte

Ajouté :

- export JSON canonique du résultat du solveur mixte ;
- SHA-256 via l'enveloppe P6-G existante ;
- conservation des approvals, résidus, bornes, diagnostics SciPy et warnings ;
- encodage des bornes non finies en `null` avec sémantique `unbounded` ;
- tables typées nœuds/conduites/compresseurs/frontières pour API/UI/rapports ;
- refus des couvertures d'entités incohérentes.

### P6-H — benchmark mixte

Ajouté :

- adaptateur des résultats mixtes vers `GasBenchmarkObservation` ;
- pression nœud, débit conduite signé, débit compresseur, ratio compresseur, débit frontière signé ;
- unités exactes uniquement, aucune conversion implicite ;
- statut solveur source conservé ;
- artefact canonique de chaîne de preuve ;
- hashes résultat PETROLE / entrée externe / sortie externe ;
- couverture exacte des observations par critères `APPROVED` ;
- `qualification_claim=false` et `certification_claim=false`.

### API d'intégration

Ajouté :

- façade `hydro_gas.stationary_equipment_api` regroupant les contrats stables du moteur mixte sans gonfler le paquet racine.

### P6-D — thermodynamique compresseur

Ajouté :

- bilan énergétique stationnaire avec enthalpie, énergie cinétique, énergie potentielle et chaleur toutes explicites ;
- convention de puissance mécanique entrante explicite ;
- fermeture par rendement isentropique sans recherche implicite de propriétés ;
- liaison possible au rendement exact du point de carte compresseur ;
- adaptateur CoolProp pour état entrée, sortie isentropique et sortie réelle ;
- conservation de la version CoolProp et des références de fluide/état/rendement/méthode ;
- post-traitement du résultat réseau mixte vers température de refoulement et puissance mécanique ;
- statut `NON_CONVERGED` conservé lorsqu'un résultat est utilisé à des fins diagnostiques.

## Ce qui n'est toujours pas autorisé comme claim

- solveur mixte benchmarké industriellement ;
- validation thermodynamique d'un gaz naturel réel ;
- puissance moteur/turbine ;
- limites constructeur ;
- recycle ;
- anti-surge opérationnel ;
- commande automatique d'un compresseur ;
- certification.

## Prochain gate

Avant d'empiler un nouveau modèle :

1. passer l'ensemble des lots post-checkpoint dans Ruff/lint/mypy/pytest/coverage ;
2. conserver CodeQL et la référence GasModels verts ;
3. corriger uniquement les défauts réellement observés ;
4. ensuite qualifier un cas thermodynamique représentatif et poursuivre vers puissance/température multi-compresseurs ou station.
