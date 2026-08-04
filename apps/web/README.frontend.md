# Frontend PETROLE

Le frontend du MVP repose sur la structure Shadcn Admin adaptée au domaine des hydrocarbures.

## Socle

- React 18 + TypeScript + Vite ;
- Tailwind CSS 4 et tokens shadcn/ui ;
- Radix UI, class-variance-authority et composants shadcn/ui ;
- TanStack Router, Query et Table ;
- React Hook Form, Zod et Zustand ;
- ECharts pour les graphiques scientifiques ;
- React Flow pour les schémas technologiques ;
- MapLibre GL JS pour la cartographie.

Clerk n'est pas utilisé : l'authentification reste fournie par le backend FastAPI de PETROLE.

## Identité visuelle

| Usage | Couleur |
|---|---|
| Bleu pétrole | `#0F4C5C` |
| Bleu profond | `#0A3540` |
| Ambre industriel | `#D98E04` |
| Fond clair | `#F5F7F8` |
| Texte principal | `#102A33` |
| Succès | `#168A5B` |
| Erreur | `#C43D3D` |
| Maintenance | `#7C5CC4` |

Les modes clair, sombre et système sont pris en charge et le choix est mémorisé localement.

## Développement

```bash
cd apps/web
npm ci
npm run check
npm run test:e2e
npm run dev
```

Le serveur Vite écoute sur le port 80 dans l'environnement de développement conteneurisé et transmet `/api` au backend FastAPI.

## Organisation principale

```text
src/
├── components/ui/          composants shadcn/ui
├── components/charts/      graphiques ECharts
├── components/maps/        cartes MapLibre
├── features/network-editor canevas React Flow
├── pages/                  écrans métier
├── router.tsx              routes TanStack Router
├── shadcn-tokens.css       design tokens PETROLE
└── theme.tsx               modes clair/sombre/système
```

## Validation

La CI frontend exécute :

1. `npm ci` ;
2. le typage TypeScript strict ;
3. le build de production Vite ;
4. `npm audit --audit-level=high` ;
5. les parcours Playwright sur les vues bureau et mobile.

La validation de pull request conserve les essais backend rapides et reproductibles. Les campagnes de qualification marquées `slow`, notamment les mesures de très grande capacité, restent séparées afin de ne pas bloquer chaque modification du frontend.

La branche de migration est `feature/frontend-shadcn-admin` et reste isolée du développement backend jusqu'à la revue visuelle et fonctionnelle.
