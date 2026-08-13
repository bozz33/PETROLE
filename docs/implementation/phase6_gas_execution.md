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
- validation des rendements, ordres de points et lignes de vitesse ;
- topologie gaz stationnaire indépendante du moteur liquide ;
- bilan massique nodal `Σm_entrant - Σm_sortant + m_externe` avec flux inverses ;
- injections/soutirages externes explicites et références de provenance ;
- résidus nodaux et globaux exposés sans tolérance industrielle codée en dur ;
- registre P6-B de modèles constitutifs avec identifiant, version, formulation, équation, source, domaine et hypothèses obligatoires ;
- états de qualification P6-B limités à `declared`, `benchmark_ready` et `benchmarked`, sans sémantique de certification ;
- preuve obligatoire pour un modèle marqué `benchmarked` ;
- binding constitutif unique par conduite vers un modèle/version et un jeu de paramètres identifié par SHA-256 ;
- références séparées de géométrie, propriétés gaz et provenance du binding ;
- diagnostic de manifeste distinguant conduite non liée, binding étranger au réseau, modèle inconnu et modèle non prêt benchmark ;
- sélection énergétique discrète P6-F sur plans déjà évalués ;
- preuve explicite de chaque contrainte obligatoire, sans faisabilité implicite ;
- candidat violant une contrainte exclu même si son énergie est inférieure ;
- classement déterministe par énergie totale puis identifiant ;
- infaisabilité explicite sans solution de secours inventée ;
- optimalité P6-F limitée à l'ensemble discret fourni, sans prétention d'optimalité continue/réseau ;
- export JSON canonique P6-G de résultats déjà calculés ;
- version de modèle, références composition/propriétés, hypothèses et diagnostics conservés dans l’export ;
- empreinte SHA-256 du contenu exporté, sans recalcul scientifique dans la couche de restitution ;
- contrat P6-H de benchmark externe indépendant du format interne du solveur de référence ;
- version, formulation, format et empreintes entrée/sortie du solveur externe obligatoires ;
- comparaison observation par observation avec grandeur, localisation, unité et provenance explicites ;
- erreurs signée, absolue et relative calculées sans seuil implicite ;
- critères optionnels mais obligatoirement pré-enregistrés et sourcés ;
- observation sans critère conservée comme non évaluée, jamais transformée en succès.

La conservation/topologie P6-B est implémentée et le choix d'un modèle constitutif est désormais traçable par manifeste. Le solveur de conduite gaz stationnaire compressible reste toutefois incomplet : aucune équation de perte de charge n'est encore exécutable tant qu'une formulation cible, ses paramètres, son domaine et ses benchmarks indépendants n'ont pas été sélectionnés et validés.

P6-F dispose désormais d'une première fondation d'énumération filtrée conforme à D07 : la couche de décision consomme uniquement des plans et preuves calculés en amont. Elle ne constitue pas encore un NLP/MILP/MINLP couplé à la physique gaz et n'autorise aucune commande compresseur.

P6-G dispose maintenant d’une fondation de restitution versionnée. P6-H dispose d'un contrat reproductible pour comparer PETROLE à GasModels.jl ou à un autre solveur externe sans coupler le modèle persistant PETROLE à leur sérialisation. Les rapports gaz complets restent toutefois bloqués par la qualification du moteur P6-B, la qualification des évaluateurs amont de P6-F et par l'exécution de benchmarks indépendants réels.

## 4. Règles scientifiques

- le fluide gaz est un domaine séparé du moteur liquide ;
- toute équation d’état ou corrélation publie son domaine, sa source et son édition ;
- aucun facteur de compressibilité, efficacité ou limite compresseur n’est inventé ;
- cartes fournisseur brutes conservées et ajustements versionnés ;
- extrapolations hors domaine refusées ou signalées explicitement ;
- line-pack et bilans de masse vérifiables ;
- les modèles stationnaires et transitoires gaz restent explicitement distincts ;
- le bilan nodal, le modèle constitutif de conduite et le modèle compresseur restent des couches distinctes ;
- aucune équation de conduite ne devient active sans modèle/version, domaine, hypothèses, paramètres et provenance explicites ;
- `benchmark_ready` et `benchmarked` sont des états techniques de validation interne, jamais une certification ;
- la sélection énergétique ne recalcule jamais la physique : énergie et preuves de contraintes viennent de modèles amont versionnés ;
- aucun plan sans preuve explicite de contraintes n'est déclaré faisable ;
- `optimality_gap=0` d'une sélection discrète signifie seulement que l'espace fourni a été entièrement parcouru ;
- la couche d’export sérialise les résultats qualifiés en amont sans les recalculer ;
- un solveur externe est identifié par sa version, sa formulation, son format et les empreintes des cas réellement exécutés ;
- aucune différence cross-solver n'est présentée comme validation si les critères n'ont pas été définis avant la comparaison.

## 5. Normes et propriété intellectuelle

Les pages officielles ASME/ISO/API servent à vérifier l’existence, le statut et l’édition. Les clauses contractuelles détaillées ne sont implémentées qu’à partir de copies légalement acquises et revues par l’expert compétent. Aucun texte protégé n’est recopié dans le dépôt.

## 6. Gate avant publication

- propriétés et composition représentatives disponibles ;
- cartes compresseurs réelles ou jeux de référence publics ;
- cas indépendants de validation ;
- revue par un ingénieur gaz/thermofluides ;
- documentation des limites et incertitudes ;
- avant l'évaluateur constitutif P6-B : formulation, paramètres, domaine et source explicitement sélectionnés ;
- avant NLP/MILP/MINLP réseau : loi constitutive P6-B validée et fonction objectif/contraintes sourcées.

## 7. Hors portée

- commande compresseur ;
- SIS/anti-surge opérationnel ;
- certification ASME/API ;
- détection de fuite opérationnelle : Phase 7.
