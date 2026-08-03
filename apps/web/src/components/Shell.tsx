import type { PropsWithChildren, ReactNode } from "react";

import { useAuth } from "../auth";
import { InternalLink, useNavigation } from "../routing";

const NAVIGATION = [
  { to: "/", label: "Vue d'ensemble", mark: "01" },
  { to: "/projets", label: "Projets et versions", mark: "02" },
  { to: "/modelisation", label: "Modélisation", mark: "03" },
  { to: "/bibliotheques", label: "Bibliothèques", mark: "04" },
  { to: "/calcul", label: "Calcul hydraulique", mark: "05" },
  { to: "/stockage", label: "Stockage et transferts", mark: "06" },
  { to: "/decision", label: "Comparaison et décision", mark: "07" },
  { to: "/donnees", label: "Données et imports", mark: "08" },
  { to: "/rapports", label: "Rapports", mark: "09" },
  { to: "/administration", label: "Administration", mark: "10" },
];

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  "/": {
    title: "Vue d'ensemble",
    subtitle: "État de la plateforme et accès aux fonctions d'ingénierie.",
  },
  "/projets": {
    title: "Projets et versions",
    subtitle: "Organisations, référentiels et modèles de calcul versionnés.",
  },
  "/modelisation": {
    title: "Modélisation",
    subtitle: "Construire et valider le réseau, ses tronçons et ses équipements.",
  },
  "/bibliotheques": {
    title: "Bibliothèques techniques",
    subtitle: "Versionner les produits, pompes, vannes, matériaux et accessoires.",
  },
  "/calcul": {
    title: "Calcul hydraulique",
    subtitle: "Préparer un cas, lancer le moteur et analyser les diagnostics.",
  },
  "/stockage": {
    title: "Stockage et transferts",
    subtitle: "Gérer les bacs, simuler les mouvements et vérifier les bilans matière.",
  },
  "/decision": {
    title: "Comparaison et décision",
    subtitle: "Classer les scénarios et rechercher une configuration de pompage faisable.",
  },  "/donnees": {
    title: "Données et imports",
    subtitle: "Contrôler, mapper et normaliser les fichiers CSV ou XLSX.",
  },
  "/rapports": {
    title: "Rapports",
    subtitle: "Générer et approuver les notes de calcul traçables.",
  },
  "/administration": {
    title: "Administration",
    subtitle: "Gérer les membres, les références normatives, les règles et l'audit.",
  },
};

export function Shell({ children }: PropsWithChildren) {
  const { path } = useNavigation();
  const metadata = PAGE_TITLES[path] ?? PAGE_TITLES["/"];
  const { user, localBypass, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <InternalLink to="/" className="brand" label="Accueil">
          <span className="brand-symbol" aria-hidden="true">
            HP
          </span>
          <span>
            <strong>HydroPlatform</strong>
            <small>Ingénierie liquide</small>
          </span>
        </InternalLink>

        <nav className="main-nav" aria-label="Navigation principale">
          {NAVIGATION.map((item) => (
            <InternalLink
              key={item.to}
              to={item.to}
              className={(isActive) => (isActive ? "nav-link active" : "nav-link")}
            >
              <span className="nav-mark">{item.mark}</span>
              <span>{item.label}</span>
            </InternalLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <span className="environment-dot" />
          <span>
            {localBypass ? "Environnement local" : user?.full_name}
            <small>{localBypass ? "Accès direct de développement" : user?.email}</small>
          </span>
        </div>
      </aside>

      <main className="main-content">
        <header className="page-header">
          <div>
            <p className="eyebrow">Plateforme Hydrocarbures</p>
            <h1>{metadata.title}</h1>
            <p>{metadata.subtitle}</p>
          </div>
          <div className="page-actions">
            <a className="button button-secondary" href="/docs" target="_blank" rel="noreferrer">
              Documentation API
            </a>
            {!localBypass ? (
              <button className="button button-ghost" onClick={() => void logout()}>
                Se déconnecter
              </button>
            ) : null}
          </div>
        </header>
        <div className="page-body">{children}</div>
      </main>
    </div>
  );
}

export function Panel({
  title,
  description,
  action,
  children,
  className = "",
}: PropsWithChildren<{
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}>) {
  return (
    <section className={"panel " + className}>
      <header className="panel-header">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}

export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="empty-state">
      <span aria-hidden="true">○</span>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

export function ErrorNotice({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "Une erreur inattendue est survenue.";
  return (
    <div className="notice notice-error" role="alert">
      <strong>Action impossible</strong>
      <span>{message}</span>
    </div>
  );
}

export function SuccessNotice({ children }: PropsWithChildren) {
  return (
    <div className="notice notice-success" role="status">
      {children}
    </div>
  );
}

export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const positive =
    normalized.includes("active") ||
    normalized.includes("approved") ||
    normalized.includes("converged") ||
    normalized.includes("completed") ||
    normalized.includes("generated") ||
    normalized === "valide" ||
    normalized === "conforme";
  const negative =
    normalized.includes("invalid") ||
    normalized.includes("failed") ||
    normalized.includes("error") ||
    normalized.includes("rejected") ||
    normalized.includes("not_converged") ||
    normalized === "invalide" ||
    normalized === "non conforme";
  const kind = negative ? "negative" : positive ? "positive" : "neutral";
  return <span className={"status-badge " + kind}>{value.replaceAll("_", " ")}</span>;
}
