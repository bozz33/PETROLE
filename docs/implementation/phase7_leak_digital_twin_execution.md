# Phase 7 — Détection de fuite et jumeau numérique

Statut : fondations R&D/produit post-SCADA, non certifiantes et non opérationnelles tant que les gates de données ne sont pas fermées.

Base de travail : `main = 6c0ed6aa1632eef0cb207f5ec3bcce9c382a140e`. Cette branche développe uniquement les briques qui peuvent être vérifiées sans prétendre disposer de données de fuite industrielles validantes.

## 1. Références projet

- D08 : API RP 1130 / API RP 1175 / API TR 1149 et intégrité ;
- D15 : distinction alerte analytique / alarme de contrôle ;
- D17 : Phase 7 ;
- D20 : pilotes, métriques et décisions Go/No-Go.

## 2. Sous-lots

1. P7-A — estimation d’état et réconciliation hydraulique ;
2. P7-B — RTTM liquide quasi temps réel ;
3. P7-C — bilan matière compensé et incertitudes ;
4. P7-D — détecteurs complémentaires : résidus, pression/débit, signatures transitoires ;
5. P7-E — fusion de preuves et score explicable ;
6. P7-F — localisation probabiliste et intervalle d’incertitude ;
7. P7-G — gestion des événements, faux positifs et performances ;
8. P7-H — jumeau numérique versionné : état estimé, modèle, données et hypothèses ;
9. P7-I — campagne de validation sur données labellisées/essais contrôlés.

## 3. Fondations déjà codées

- métriques de détection à partir de TP/FP/FN/TN et délais observés ;
- bilan matière compensé `entrée - sortie - variation d’inventaire` ;
- propagation RSS des incertitudes-types fournies pour le bilan ;
- résidu normalisé uniquement lorsque l’incertitude combinée est non nulle ;
- aucun seuil de fuite implicite ni génération d’alarme ;
- variables de jumeau en SI avec unité et référence de provenance obligatoires ;
- snapshots immuables ordonnés, horodatés UTC et adressés par empreinte `sha256` canonique ;
- comparaison de snapshots uniquement pour une même version de modèle, séquence croissante et unités cohérentes ;
- matching explicite événements labellisés ↔ alertes observées, sans fenêtre temporelle cachée ;
- fusion de preuves pondérées sans seuil de fuite implicite ;
- contrat de localisation avec estimation et intervalle d'incertitude fournis explicitement ;
- critères de campagne P7-I pré-enregistrés avec provenance obligatoire ;
- évaluation factuelle de précision, rappel, spécificité, taux de faux positifs, délais et taille de campagne contre les seuls critères configurés ;
- métrique absente conservée comme non évaluable au lieu d'être interprétée comme un succès.

Le snapshot versionné est une brique de traçabilité. Il ne constitue pas encore l’estimation d’état P7-A, le RTTM P7-B, un détecteur P7-D ou une localisation P7-F opérationnelle.

La fondation P7-I permet désormais de figer et évaluer les critères de campagne, mais elle ne ferme pas la gate de validation : les données labellisées/essais contrôlés, les seuils approuvés par l'opérateur et la revue indépendante restent nécessaires.

## 4. Règles non négociables

- une alerte PETROLE est une **suspicion analytique**, jamais un ordre d’arrêt ;
- aucune performance de détection/localisation n’est annoncée sans jeu d’essai indépendant ;
- les seuils et objectifs sont convenus avec l’opérateur, jamais codés arbitrairement ;
- incertitudes de mesure, synchronisation et indisponibilités sont incluses dans l’analyse ;
- faux positifs, faux négatifs, sensibilité, temps de détection et disponibilité sont mesurés ;
- séparation entraînement/calibration/validation/test si des méthodes apprenantes sont utilisées ;
- un critère P7-I sans métrique observable reste explicitement non évaluable ;
- la décision finale Go/No-Go reste humaine et indépendante du calcul des métriques.

## 5. Référentiel API

API RP 1175 définit le cadre de gestion du programme de détection ; API RP 1130 traite la surveillance computationnelle. Les détails normatifs sont implémentés uniquement à partir des éditions légalement acquises et approuvées par l’équipe métier. Le dépôt conserve des règles internes synthétiques et la référence d’édition, jamais le texte protégé.

## 6. Gates avant code opérationnel

- Phase 5 read-only qualifiée ;
- données synchronisées et métrologie documentée ;
- événements labellisés ou essais de fuite contrôlés ;
- critères de performance pré-enregistrés ;
- procédure opérateur de traitement des alertes ;
- revue indépendante de la campagne.

## 7. Hors portée

- déclenchement automatique SIS/ESD ;
- fermeture automatique de vanne ;
- revendication de conformité/certification API ;
- usage sur réseau critique sans pilote accepté.
