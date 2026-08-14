# PETROLE — plan maître de tout le développement restant

Statut : **MASTER_BACKLOG_EXECUTABLE — 14 août 2026**.

Ce document transforme D01, D10, D16, D17, D20 et l'état réel des branches en ordre d'exécution. Il distingue ce qui peut être développé immédiatement de ce qui exige des données, un site, un fabricant, un expert ou une décision de release.

## 1. Principes non négociables

1. `main` reste gelé tant que la cérémonie de release MVP n'est pas explicitement exécutée.
2. Aucune branche post-MVP ne doit être fusionnée dans `main` par opportunisme.
3. Aucun seuil scientifique, industriel, réglementaire ou HSE n'est inventé dans le code.
4. Aucun résultat synthétique ou benchmark open source n'est présenté comme validation terrain.
5. Les moteurs déterministes restent séparés de l'IA, de l'interface et des règles normatives.
6. Toute nouvelle physique doit avoir : source, domaine, hypothèses, unités, cas de référence et tests.
7. Toute connexion OT reste en lecture seule tant qu'une autre architecture n'a pas été formellement approuvée.
8. Une CI verte prouve la qualité du logiciel testé ; elle ne remplace jamais la revue scientifique, l'acceptation opérateur ou une certification.

## 2. État de release et intégration

### R0 — fermer officiellement le MVP 1.0

État courant : `main` reste la baseline `6c0ed6aa1632eef0cb207f5ec3bcce9c382a140e`. Les tags visibles restent `v0.1.0-rc.1` et `v0.2.0-rc.1`; aucun `v1.0.0-mvp` n'est actuellement publié.

Travail restant :

- exécuter la checklist d'acceptation finale du candidat MVP ;
- vérifier la totalité des gates CI sur le commit exact de release ;
- enregistrer les validations/revues attendues ;
- signer la release selon la politique retenue ;
- créer le tag `v1.0.0-mvp` uniquement après acceptation ;
- publier les notes de release et les checksums/artefacts ;
- conserver la baseline immuable utilisée pour le pilote.

Type de dépendance : **décision/revue/release**, pas développement scientifique.

### R1 — consolider Phase 2 / Pilote V1

DAG actuelle :

```text
main
 ├─ #20 V1-A1/A2 qualité mesures
 │    └─ #21 V1-A3 séries temporelles
 │         └─ #22 V1-B mesure ↔ modèle
 │              ├─ #30 V1-E1 RPT-07 qualité
 │              ├─ #31 V1-F gates sécurité pilote
 │              └─ #33 V1-C calibration contrôlée
 │                   └─ #34 V1-E2 RPT-08 calibration
 │                        └─ #35 V1-G preuves PIL-01…PIL-12
 └─ #23 V1-D résultats ingénieur avancés
```

Ordre de consolidation :

1. créer une branche d'intégration post-MVP à partir du tag officiel ;
2. rebaser/intégrer #20 ;
3. intégrer #21 ;
4. intégrer #22 ;
5. intégrer les branches parallèles #23, #30 et #31 en résolvant les conflits sur la baseline consolidée ;
6. intégrer #33 puis #34 puis #35 ;
7. exécuter migrations depuis une base vierge et depuis la version précédente ;
8. exécuter tests API, backend, frontend, E2E, sécurité, rapports et couverture ;
9. vérifier le lignage des données et les contrats D09/D12 ;
10. produire une baseline V1 pilote versionnée.

Travail externe restant : vraies données terrain distinctes pour valider calibration, sécurité pilote et dossier D20.

## 3. Phase 3 — analytics, tendances et prévisions

Branche/PR : #24, volontairement dépendante de la baseline séries temporelles Phase 2.

Déjà fondé : agrégations/tendances, séparation chronologique train/validation/test, OLS contrôlé, comparaison explicite à une baseline persistence/last-value, métriques sans seuil métier caché.

Reste à développer :

- rebase sur Phase 2 consolidée ;
- profils de périodes et horizons métier versionnés ;
- agrégations multi-régimes et fenêtres de qualité ;
- diagnostics latence, stagnation, trous et dérive dans les vues métier ;
- suivi historique des KPI mesure-modèle par équipement/régime ;
- registre de features et version des transformations ;
- prévisions multi-horizons lorsque le cas d'usage le justifie ;
- intervalles/incertitude si une méthode est sélectionnée et validée ;
- indicateurs de maintenance conditionnelle non-sûreté ;
- API de campagnes analytics ;
- dashboards ingénieur et exports versionnés ;
- tests de non-régression sur datasets représentatifs ;
- politique de dégradation lorsque la qualité des données est insuffisante.

Gates externes :

- historique représentatif de plusieurs régimes ;
- définition métier des horizons utiles ;
- critères d'acceptation approuvés ;
- validation réellement hors échantillon / terrain.

## 4. Phase 4 — multiproduits et transitoires liquides

Branche/PR : #25.

Déjà fondé : contrat Phase 4, interfaces temporelles, position spatiale des interfaces selon hypothèse piston/plug-flow, premières briques transitoires et séparation explicite entre modèle générique et modèles d'équipements.

Reste à développer :

### P4-A — multiproduits

- modèle physique sélectionné pour largeur/mélange d'interface ;
- dispersion/mélange avec domaine de validité sourcé ;
- propriétés dépendantes de température/composition si retenues ;
- volumes contaminés et règles de coupure qualité ;
- séquences de lots et contraintes de stockage ;
- planification et restitution des interfaces.

### P4-B — transitoires

- fermer/valider le solveur MOC retenu ;
- stratégie CFL/maillage/pas de temps ;
- étude de convergence maillage/temps ;
- conditions limites réservoir amont/aval ;
- vanne avec loi de fermeture sourcée ;
- pompe en régime transitoire avec modèle sélectionné ;
- clapet/check valve si retenu ;
- arrêt/démarrage et événements temporels ;
- dispositifs de protection si dans le périmètre ;
- cavitation/séparation de colonne uniquement après modèle et benchmark spécialisé ;
- profils `P(x,t)`, `Q(x,t)`, `H(x,t)` et événements ;
- API/UI/rapports transitoires.

Gates externes : publications/cas indépendants, revue thermofluides, événement instrumenté ou test contrôlé avant validation industrielle.

## 5. Phase 5 — SCADA / historian read-only

Branche/PR : #26, à rebaser sur la baseline Phase 2 consolidée.

Déjà fondé : politique read-only, simulateur déterministe de subscriptions, séquences/Republish, distinction ACK transport vs acquittement procédé, recovery plan, contrat P5-C identité/certificat/trust/security policy.

Reste à développer :

### P5-A — passerelle réelle

- service/gateway dédié open62541 selon D14 ;
- adapter interne stable entre PETROLE et la passerelle ;
- découverte/configuration explicite des endpoints ;
- `SignAndEncrypt` ;
- certificats client/serveur et trust list ;
- vérification ApplicationUri et identité endpoint ;
- gestion expiration/révocation/rotation ;
- aucune clé privée dans la base applicative.

### P5-B — acquisition

- Browse contrôlé ;
- Read ;
- Subscription/MonitoredItems ;
- Publish/SubscriptionAcknowledgements ;
- Republish ;
- HistoryRead si autorisé ;
- timestamps source/serveur ;
- StatusCode/qualité ;
- reconnexion ;
- buffer borné ;
- checkpoint ;
- déduplication ;
- backfill contrôlé.

### P5-C — normalisation/historian

- mapping tag → unité SI → objet métier ;
- persistance séries brute/normalisée ;
- adapter historian réellement retenu ;
- MQTT read-only si besoin confirmé ;
- santé/latence des connecteurs ;
- métriques et audit ;
- UI diagnostic connecteur.

### P5-D — déploiement OT

- segmentation/DMZ ;
- règles réseau minimales ;
- secrets/certificats externalisés ;
- qualification OT-0 à OT-5 ;
- test sur serveur/lab OPC UA réel ;
- procédure de désactivation immédiate de la passerelle.

Gates externes : architecture OT approuvée, certificats/site lab, accès historian/OPC UA réel, spécialiste automatisme/cybersécurité.

## 6. Phase 6 — gazoducs et compression

Branche/PR : #27.

### P6-H0 — fermer le protocole benchmark

- CI complète du contrat `DRAFT/APPROVED` ;
- aucun critère réel exécutable tant que son `approval_ref` n'existe pas ;
- fixer le protocole de comparaison du cas GasModels déjà reproduit ;
- ajouter plusieurs cas indépendants ;
- conserver GasModels comme référence externe et non comme vérité implicite du cœur.

### P6-A — propriétés gaz

Déjà : composition molaire, masse molaire, état `p/T/M/Z`, densité Z explicite, adapter CoolProp contrôlé.

Reste :

- modèles/compositions réellement retenus pour mélanges ;
- calcul de `Z(P,T,composition)` seulement via méthode sélectionnée/versionnée ;
- densité, vitesse du son et propriétés nécessaires cohérentes avec la même méthode ;
- enveloppes de validité ;
- provenance labo/fournisseur ;
- interpolation/erreurs hors domaine ;
- cas de comparaison indépendants.

### P6-B — vrai solveur stationnaire gaz

Déjà : topologie, bilan massique, registre constitutif, Weymouth-SI, paramètres canoniques/hashés, résidu par conduite, assemblage des résidus réseau sur état candidat.

Ordre de développement restant :

1. valider l'assemblage réseau candidat ;
2. définir les familles de problèmes autorisées et conditions limites ;
3. définir les inconnues : pressions ou pressions au carré, débits, variables machines ;
4. définir la mise à l'échelle des variables/résidus sans valeur arbitraire ;
5. écrire le mapping état ↔ vecteur d'inconnues ;
6. écrire la fonction résiduelle pure du système ;
7. sélectionner l'adapter de solveur non linéaire ;
8. statuts explicites convergé/non convergé/hors domaine/données insuffisantes ;
9. diagnostics d'itération sans masquer un échec ;
10. tests une conduite ;
11. tests série ;
12. tests réseau ramifié ;
13. flux inverse ;
14. injections/soutirages ;
15. comparaison GasModels et autre référence indépendante ;
16. seulement après qualification, élargir à d'autres formulations si le produit le demande.

Interdit avant les gates : déclarer une formule universelle, déduire une tolérance de GasModels, ou appeler un résidu proche de zéro une certification.

### P6-C — line-pack

Déjà : inventaire segmenté `ΣρAΔx`.

Reste :

- couplage aux états du réseau ;
- propriétés par segment ;
- inventaire par conduite/réseau ;
- différence de line-pack entre états ;
- scénarios injection/soutirage ;
- benchmark conduite uniforme ;
- restitution/API/UI.

### P6-D — compresseurs

Déjà : cartes versionnées, interpolation dans le domaine, refus d'extrapolation, enveloppes de débit.

Reste :

- point thermodynamique aspiration/refoulement ;
- rapport de compression ;
- température de refoulement selon méthode retenue ;
- rendement/puissance avec données réelles ;
- lignes de vitesse ;
- choke/stonewall ;
- anti-surge comme **marge analytique**, jamais commande de protection ;
- lois de similitude uniquement avec domaine sourcé ;
- configurations série/parallèle ;
- limites driver/moteur/turbine si fournies ;
- benchmarks carte fabricant/publics.

### P6-E — stations gaz

- coupler unités, bypass, vannes et régulateurs ;
- états disponibilité/service/secours ;
- injections/soutirages ;
- régulation de pression ;
- limites station ;
- intégrer les équations machines au solveur réseau ;
- diagnostics de non-faisabilité ;
- scénarios station indisponible.

### P6-F — optimisation énergétique

Déjà : sélection exhaustive déterministe parmi plans déjà évalués.

Reste après qualification du solveur :

- génération de plans physiques ;
- coûts/énergie sourcés ;
- variables continues si nécessaires ;
- NLP ciblé ;
- MILP si formulation justifiée ;
- MINLP uniquement si le besoin et le modèle le justifient ;
- gap/statut solveur exposé ;
- comparaison exhaustive sur petits cas ;
- aucun ordre de commande procédé.

### P6-G — produit/UI/rapports gaz

- API de modèle gaz et scénarios ;
- éditeur réseau gaz ;
- vues pression/débit/température/line-pack ;
- cartes compresseur avec point opératoire ;
- marges et diagnostics ;
- export CSV/Excel ;
- rapport PDF versionné ;
- hypothèses, méthodes, versions, warnings et sources dans chaque rapport.

### P6-H — validation/pilote gaz

- réseau analytique simple ;
- plusieurs cas GasModels ;
- pandapipes ou autre référence indépendante si formulation alignable ;
- logiciel industriel si accessible ;
- cartes compresseur de référence ;
- cas line-pack ;
- revue thermofluides ;
- pilote E D17 avec composition, cartes, pression, température et demande réelles.

## 7. Phase 7 — fuite, RTTM et jumeau numérique

Branche/PR : #28.

Déjà fondé : contrats de détection, métriques et gate de campagne de validation sans seuil industriel par défaut.

Reste à développer :

- sélectionner/formaliser la méthode d'estimation d'état ;
- RTTM liquide cohérent avec le moteur transitoire validé ;
- réconciliation mesures/modèle ;
- bilan matière compensé avec incertitudes ;
- détecteurs statistiques complémentaires ;
- dérive/rupture/innovation résiduelle selon méthodes sélectionnées ;
- fusion de preuves sans masquer l'origine de chaque alerte ;
- localisation probable et intervalle/incertitude ;
- gestion des données manquantes et capteurs bad ;
- métriques précision/rappel/spécificité/faux positifs/délai ;
- seuils pré-enregistrés par protocole/site ;
- version du jumeau numérique et état de calibration ;
- API/UI événements et preuves ;
- procédures de revue opérateur ;
- aucune commande automatique de sécurité.

Gates externes critiques : Phase 5 read-only qualifiée, données labellisées ou essais contrôlés, exigences de performance du site, revue API 1130/API 1175 et opérateur.

## 8. Phase 8 — industrialisation

Branche/PR : #29.

Déjà fondé : contrats de reliability/recovery/load/qualification, provenance, identité/certificats, evidence chaos et gate d'industrialisation logiciel.

Reste à réaliser réellement dans l'infrastructure :

- architecture HA PostgreSQL ;
- réplication/backup/WAL/PITR ;
- restauration réellement chronométrée et prouvée ;
- stockage objet redondant ;
- haute disponibilité API/workers ;
- files de tâches résilientes ;
- observabilité métriques/logs/traces ;
- SLI/SLO approuvés ;
- alerting et astreinte ;
- OIDC/MFA avec IdP retenu ;
- RBAC multi-sites ;
- isolation tenants/sites ;
- gestion secrets/KMS/Vault selon environnement ;
- PKI/certificats/rotation ;
- SBOM/signature/provenance des images ;
- scans de vulnérabilités et politique patch ;
- canary/rollback ;
- migrations blue/green ou stratégie équivalente ;
- charge réelle ;
- chaos/failover réel ;
- tests réseau dégradé ;
- runbooks ;
- support/incident ;
- procédure upgrade ;
- multi-sites ;
- formation administrateur/opérateur ;
- validation D20 sur site.

Gates externes : infrastructure cible, IdP, PKI, contraintes réseau, opérateur, SLA, politique cybersécurité et exigences réglementaires locales.

## 9. Validation publique et données

PR #17 reste une piste parallèle.

Déjà : Seaway/LANL et EC-01 apportent des preuves comparatives utiles ; les candidats prédictifs publics restent bloqués par des variables manquantes ou des données SCADA non publiques.

Reste :

- ne jamais convertir un candidat incomplet en validation prédictive ;
- poursuivre la recherche de datasets complets ;
- obtenir des partenariats pour données réelles ;
- versionner droits/licences/provenance ;
- séparer `PUBLISHED`, `MEASURED`, `DERIVED`, `ASSUMPTION` ;
- tenir les grandeurs de vérité hors des entrées lorsque l'on revendique une validation prédictive.

## 10. Travail transverse obligatoire

### Normes et règles

- vérifier l'édition applicable par projet ;
- conserver les éditions et références ;
- ne jamais recopier des clauses protégées ;
- implémenter les exigences détaillées uniquement depuis copies légalement accessibles et revues ;
- prévoir le contexte Côte d'Ivoire / pays d'installation.

### Données

- modèle de provenance commun ;
- checksum des jeux de validation ;
- immutabilité brut/normalisé/corrigé ;
- qualité explicite ;
- politique de rétention ;
- anonymisation des pilotes si nécessaire.

### API / produit

- contrats versionnés ;
- erreurs structurées ;
- permissions ;
- pagination/filtrage ;
- tâches longues ;
- audit ;
- vues d'ingénierie ;
- export reproductible.

### Qualité

Pour chaque incrément :

- Ruff format ;
- Ruff lint ;
- mypy ;
- tests unitaires ;
- tests intégration ;
- couverture ;
- cas scientifique si physique ;
- migrations ;
- dérive de schéma ;
- frontend build ;
- Playwright ;
- CodeQL ;
- images de production ;
- documentation.

## 11. Ordre d'exécution recommandé à partir de maintenant

```text
A. Fermer CI P6-H DRAFT/APPROVED
B. Valider l'assemblage des résidus réseau P6-B
C. Écrire/valider le plan maître présent
D. Préparer plusieurs benchmarks P6-B sans inventer de seuil
E. Faire approuver les critères de benchmark
F. Implémenter le contrat conditions limites/inconnues
G. Implémenter le mapping état ↔ variables
H. Implémenter le premier solveur stationnaire gaz
I. Étendre aux réseaux ramifiés
J. Coupler propriétés gaz qualifiées
K. Coupler compresseurs/stations
L. Coupler line-pack
M. Optimisation gaz
N. API/UI/rapports gaz
O. Validation/pilote gaz
P. Consolider les branches post-MVP dans leur ordre après release officielle
Q. Fermer Phase 3, puis Phase 4, Phase 5 selon leurs gates
R. Phase 7 seulement avec données/OT qualifiés
S. Phase 8 avec infrastructure réelle et pilote
```

L'ordre d'intégration Git ne doit pas être confondu avec l'ordre R&D : des branches indépendantes peuvent avancer en parallèle, mais aucune ne doit contourner le gate scientifique de la capacité dont elle dépend.

## 12. Prochain incrément de code après ce document

Le prochain incrément P6-B est l'assemblage de résidus réseau sur état candidat : pressions par nœud + débits par conduite + frontières + paramètres Weymouth → résidus massiques et constitutifs séparés. Il prépare le futur solveur sans choisir prématurément une normalisation ou une méthode de racines.

Après sa CI, le prochain incrément autorisé sera le **contrat de problème stationnaire** : classification des conditions limites et détermination structurale des inconnues, toujours sans convergence artificielle.
