import type { FormEvent, PropsWithChildren, ReactNode } from "react";

import { useAuth } from "../auth";
import { InternalLink, useNavigation } from "../routing";
import { useTheme } from "../theme";

type IconName =
  | "dashboard"
  | "folder"
  | "network"
  | "library"
  | "calculator"
  | "tank"
  | "decision"
  | "database"
  | "report"
  | "settings"
  | "search"
  | "bell"
  | "sun"
  | "moon"
  | "droplet";

const NAVIGATION: Array<{ to: string; label: string; icon: IconName }> = [
  { to: "/", label: "Tableau de bord", icon: "dashboard" },
  { to: "/projets", label: "Projets", icon: "folder" },
  { to: "/modelisation", label: "Modélisation", icon: "network" },
  { to: "/bibliotheques", label: "Bibliothèques", icon: "library" },
  { to: "/calcul", label: "Calcul hydraulique", icon: "calculator" },
  { to: "/stockage", label: "Stockage et transferts", icon: "tank" },
  { to: "/decision", label: "Comparaison et décision", icon: "decision" },
  { to: "/donnees", label: "Données et imports", icon: "database" },
  { to: "/rapports", label: "Rapports", icon: "report" },
  { to: "/administration", label: "Administration", icon: "settings" },
];

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  "/": {
    title: "Tableau de bord",
    subtitle: "Vue consolidée de la plateforme, des projets et de l'état des calculs.",
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
  },
  "/donnees": {
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
  const { resolvedTheme, toggleTheme } = useTheme();
  const initials = initialsOf(user?.full_name ?? "Alain Kouassi");

  function search(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <InternalLink to="/" className="brand" label="Accueil PETROLE">
          <span className="brand-symbol" aria-hidden="true">
            <Icon name="droplet" />
          </span>
          <span>
            <strong>PETROLE</strong>
            <small>Hydraulique & stockage</small>
          </span>
        </InternalLink>

        <p className="nav-section-label">Espace de travail</p>
        <nav className="main-nav" aria-label="Navigation principale">
          {NAVIGATION.map((item) => (
            <InternalLink
              key={item.to}
              to={item.to}
              className={(isActive) => (isActive ? "nav-link active" : "nav-link")}
            >
              <span className="nav-mark" aria-hidden="true">
                <Icon name={item.icon} />
              </span>
              <span>{item.label}</span>
            </InternalLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <span className="environment-dot" aria-hidden="true" />
          <span>
            {localBypass ? "Environnement local" : user?.full_name}
            <small>{localBypass ? "Services de développement actifs" : user?.email}</small>
          </span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-context">
            <span>Plateforme</span>
            <span aria-hidden="true">/</span>
            <strong>{metadata.title}</strong>
          </div>

          <div className="topbar-actions">
            <form className="global-search" role="search" onSubmit={search}>
              <Icon name="search" />
              <input aria-label="Rechercher" placeholder="Rechercher…" type="search" />
              <kbd>⌘ K</kbd>
            </form>
            <button
              className="icon-button"
              type="button"
              onClick={toggleTheme}
              aria-label={resolvedTheme === "dark" ? "Activer le mode clair" : "Activer le mode sombre"}
              title={resolvedTheme === "dark" ? "Mode clair" : "Mode sombre"}
            >
              <Icon name={resolvedTheme === "dark" ? "sun" : "moon"} />
            </button>
            <button className="icon-button" type="button" aria-label="Notifications">
              <Icon name="bell" />
              <span className="notification-dot" aria-hidden="true" />
            </button>
            <div className="profile-chip" title={user?.email ?? "Profil local"}>
              <span className="profile-avatar">{initials}</span>
              <span className="profile-copy">
                <strong>{localBypass ? "Administrateur" : user?.full_name}</strong>
                <small>{localBypass ? "Mode local" : "Compte actif"}</small>
              </span>
            </div>
          </div>
        </header>

        <header className="page-header">
          <div>
            <h1>{metadata.title}</h1>
            <p>{metadata.subtitle}</p>
          </div>
          <div className="page-actions">
            <a className="button button-secondary" href="/docs" target="_blank" rel="noreferrer">
              Documentation API
            </a>
            {!localBypass ? (
              <button className="button button-ghost" type="button" onClick={() => void logout()}>
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

export function EmptyState({ title, detail }: { title: string; detail: string }) {
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

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") || "PT";
}

function Icon({ name }: { name: IconName }) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  const paths: Record<IconName, ReactNode> = {
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    folder: <><path d="M3 7.5h6l2 2h10v8.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 7.5V6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v1.5"/></>,
    network: <><circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="m7 11 10-5M7 13l10 5"/></>,
    library: <><path d="M4 5h5v14H4zM10 5h5v14h-5zM16 6l4-1 2 13-4 1z"/></>,
    calculator: <><rect x="4" y="2.5" width="16" height="19" rx="2"/><path d="M7 6h10v4H7zM8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01"/></>,
    tank: <><ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v14c0 1.7 14 1.7 14 0V5M5 12c0 1.7 14 1.7 14 0"/></>,
    decision: <><path d="M4 5h7v6H4zM13 13h7v6h-7zM11 8h4a2 2 0 0 1 2 2v3M9 11v3a2 2 0 0 0 2 2h2"/></>,
    database: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></>,
    report: <><path d="M6 3h9l3 3v15H6z"/><path d="M14 3v4h4M9 11h6M9 15h6M9 19h4"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1z"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7"/><path d="M10 19h4"/></>,
    sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></>,
    moon: <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.5 6.5 0 0 0 21 12.8z"/>,
    droplet: <path d="M12 2.5S5.5 10 5.5 15a6.5 6.5 0 0 0 13 0C18.5 10 12 2.5 12 2.5z"/>,
  };

  return <svg {...common}>{paths[name]}</svg>;
}
