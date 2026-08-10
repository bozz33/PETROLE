# Phase 7 — Détection de fuite et jumeau numérique

Statut : contrat R&D/produit post-SCADA, non certifiant et non opérationnel tant que les gates de données ne sont pas fermées.

Base de travail : `main = 6c0ed6aa1632eef0cb207f5ec3bcce9c382a140e`. Cette branche contient d’abord le contrat ; l’implémentation dépendra des sorties Phase 5 et des données labellisées.

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

## 3. Règles non négociables

- une alerte PETROLE est une **suspicion analytique**, jamais un ordre d’arrêt ;
- aucune performance de détection/localisation n’est annoncée sans jeu d’essai indépendant ;
- les seuils et objectifs sont convenus avec l’opérateur, jamais codés arbitrairement ;
- incertitudes de mesure, synchronisation et indisponibilités sont incluses dans l’analyse ;
- faux positifs, faux négatifs, sensibilité, temps de détection et disponibilité sont mesurés ;
- séparation entraînement/calibration/validation/test si des méthodes apprenantes sont utilisées.

## 4. Référentiel API

API RP 1175 définit le cadre de gestion du programme de détection ; API RP 1130 traite la surveillance computationnelle. Les détails normatifs sont implémentés uniquement à partir des éditions légalement acquises et approuvées par l’équipe métier. Le dépôt conserve des règles internes synthétiques et la référence d’édition, jamais le texte protégé.

## 5. Gates avant code opérationnel

- Phase 5 read-only qualifiée ;
- données synchronisées et métrologie documentée ;
- événements labellisés ou essais de fuite contrôlés ;
- critères de performance pré-enregistrés ;
- procédure opérateur de traitement des alertes ;
- revue indépendante de la campagne.

## 6. Hors portée

- déclenchement automatique SIS/ESD ;
- fermeture automatique de vanne ;
- revendication de conformité/certification API ;
- usage sur réseau critique sans pilote accepté.
