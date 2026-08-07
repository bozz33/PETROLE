import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";

import { AuthProvider } from "./auth";
import { Shell } from "./components/Shell";
import { AdministrationPage } from "./pages/AdministrationPage";
import { BibliothequesPage } from "./pages/BibliothequesPage";
import { CalculPage } from "./pages/CalculPage";
import { DecisionPage } from "./pages/DecisionPage";
import { DonneesPage } from "./pages/DonneesPage";
import { ModelisationPage } from "./pages/ModelisationPage";
import { ProjetsPage } from "./pages/ProjetsPage";
import { RapportsPage } from "./pages/RapportsPage";
import { ScenariosPage } from "./pages/ScenariosPage";
import { StockagePage } from "./pages/StockagePage";
import { TableauBordPage } from "./pages/TableauBordPage";
import { VisualisationReseauPage } from "./pages/VisualisationReseauPage";

const rootRoute = createRootRoute({
  component: RootLayout,
  notFoundComponent: NotFoundPage,
});

const applicationRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "_application",
  component: ApplicationLayout,
});

const dashboardRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "/",
  component: TableauBordPage,
});

const projectsRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "projets",
  component: ProjetsPage,
});

const modelingRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "modelisation",
  component: ModelisationPage,
});

const networkVisualisationRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "reseau",
  component: VisualisationReseauPage,
});

const librariesRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "bibliotheques",
  component: BibliothequesPage,
});

const scenariosRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "scenarios",
  component: ScenariosPage,
});

const calculationRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "calcul",
  component: CalculPage,
});

const storageRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "stockage",
  component: StockagePage,
});

const decisionRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "decision",
  component: DecisionPage,
});

const dataRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "donnees",
  component: DonneesPage,
});

const reportsRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "rapports",
  component: RapportsPage,
});

const administrationRoute = createRoute({
  getParentRoute: () => applicationRoute,
  path: "administration",
  component: AdministrationPage,
});

const applicationTree = applicationRoute.addChildren([
  dashboardRoute,
  projectsRoute,
  modelingRoute,
  networkVisualisationRoute,
  librariesRoute,
  scenariosRoute,
  calculationRoute,
  storageRoute,
  decisionRoute,
  dataRoute,
  reportsRoute,
  administrationRoute,
]);

const routeTree = rootRoute.addChildren([applicationTree]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
  defaultPreloadStaleTime: 0,
  scrollRestoration: true,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

function RootLayout() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}

function ApplicationLayout() {
  return (
    <Shell>
      <Outlet />
    </Shell>
  );
}

function NotFoundPage() {
  return (
    <main className="access-page">
      <section className="access-card">
        <p className="eyebrow">Erreur 404</p>
        <h1>Page introuvable</h1>
        <p className="access-detail">
          L'adresse demandée n'appartient pas à l'espace de travail PETROLE.
        </p>
        <a className="button button-primary" href="/">
          Retour au tableau de bord
        </a>
      </section>
    </main>
  );
}
