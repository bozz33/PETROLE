# ADR-005 — Système SI en interne

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

Les erreurs d'unités sont la première cause d'erreur dans les logiciels d'ingénierie hydraulique.

## Décision

Le stockage et le calcul utilisent exclusivement le **système SI cohérent** (Pa, m³/s, m, K, Pa·s, W, J). Les unités d'affichage sont converties aux frontières de l'application avec **Pint**, et la valeur d'origine ainsi que son unité sont conservées.

## Conséquences

Positif : le noyau scientifique ne manipule jamais d'unité ambiguë ; les conversions sont testables isolément.

Négatif : chaque entrée utilisateur exige une unité explicite ; c'est un choix délibéré (NFR-UX-002).
