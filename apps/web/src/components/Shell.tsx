import {
  Bell,
  BookOpen,
  Calculator,
  ChevronLeft,
  CircleDot,
  Database,
  Droplet,
  FileText,
  Folder,
  GitCompareArrows,
  LayoutDashboard,
  LogOut,
  Map,
  Menu,
  Moon,
  Network,
  Search,
  Settings,
  Sun,
  type LucideIcon,
} from "lucide-react";
import {
  type FormEvent,
  type PropsWithChildren,
  type ReactNode,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useAuth } from "../auth";
import { InternalLink, useNavigation } from "../routing";
import { useTheme } from "../theme";

interface NavigationItem {
  to: string;
  label: string;
  icon: LucideIcon;
  description: string;
}

const NAVIGATION: NavigationItem[] = [
  {
    to: "/",
    label: "Tableau de bord",
    icon: LayoutDashboard,
    description: "Vue générale des projets et services",
  },
  {
    to: "/projets",
    label: "Projets",
    icon: Folder,
    description: "Projets, versions et scénarios",
  },
  {
    to: "/modelisation",
    label: "Modélisation",
    icon: Network,
    description: "Réseaux, tronçons et équipements",
  },
  {
    to: "/reseau",
    label: "Visualisation du réseau",
    icon: Map,
    description: "Schéma technologique et cartographie",
  },
  {
    to: "/bibliotheques",
    label: "Bibliothèques",
    icon: BookOpen,
    description: "Produits, pompes, vannes et matériaux",
  },
  {
    to: "/calcul",
    label: "Calcul hydraulique",
    icon: Calculator,
    description: "Lancer et analyser les simulations",
  },
  {
    to: "/stockage",
    label: "Stockage et transferts",
    icon: CircleDot,
    description: "Bacs, mouvements et bilans matière",
  },
  {
    to: "/decision",
    label: "Comparaison et décision",
    icon: GitCompareArrows,
    description: "Comparer et optimiser les scénarios",
  },
  {
    to: "/donnees",
    label: "Données et imports",
    icon: Database,
    description: "Importer, contrôler et normaliser",
  },
  {
    to: "/rapports",
    label: "Rapports",
    icon: FileText,
    description: "Notes de calcul et approbations",
  },
  {
    to: "/administration",
    label: "Administration",
    icon: Settings,
    description: "Membres, normes, règles et audit",
  },
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
  "/reseau": {
    title: "Visualisation du réseau",
    subtitle: "Explorer le schéma technologique et la cartographie du pipeline.",
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

const SIDEBAR_STORAGE_KEY = "petrole-sidebar-collapsed";

export function Shell({ children }: PropsWithChildren) {
  const { path, navigate } = useNavigation();
  const metadata = PAGE_TITLES[path] ?? PAGE_TITLES["/"];
  const { user, localBypass, logout } = useAuth();
  const { resolvedTheme, toggleTheme } = useTheme();
  const [commandOpen, setCommandOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true",
  );
  const initials = initialsOf(user?.full_name ?? "Alain Kouassi");

  const filteredNavigation = useMemo(() => {
    const query = commandQuery.trim().toLocaleLowerCase("fr");
    if (!query) {
      return NAVIGATION;
    }
    return NAVIGATION.filter((item) =>
      `${item.label} ${item.description}`.toLocaleLowerCase("fr").includes(query),
    );
  }, [commandQuery]);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase("fr") === "k") {
        event.preventDefault();
        setCommandOpen((current) => !current);
      }
      if (event.key === "Escape") {
        setCommandOpen(false);
        setMobileSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [path]);

  useEffect(() => {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  function search(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setCommandOpen(true);
  }

  function choose(item: NavigationItem): void {
    navigate(item.to);
    setCommandOpen(false);
    setCommandQuery("");
  }

  return (
    <div className={`app-shell${sidebarCollapsed ? " sidebar-collapsed" : ""}`}>
      <a className="skip-link" href="#main-content">
        Aller au contenu principal
      </a>

      {mobileSidebarOpen ? (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Fermer la navigation"
          onClick={() => setMobileSidebarOpen(false)}
        />
      ) : null}

      <aside
        className={`sidebar${sidebarCollapsed ? " is-collapsed" : ""}${
          mobileSidebarOpen ? " is-mobile-open" : ""
        }`}
      >
        <button
          className="sidebar-toggle"
          type="button"
          onClick={() => setSidebarCollapsed((current) => !current)}
          aria-label={sidebarCollapsed ? "Déployer la barre latérale" : "Réduire la barre latérale"}
          title={sidebarCollapsed ? "Déployer" : "Réduire"}
        >
          <ChevronLeft aria-hidden="true" />
        </button>

        <InternalLink to="/" className="brand" label="Accueil PETROLE">
          <span className="brand-symbol" aria-hidden="true">
            <Droplet />
          </span>
          <span className="brand-copy">
            <strong>PETROLE</strong>
            <small>Hydraulique & stockage</small>
          </span>
        </InternalLink>

        <p className="nav-section-label">Espace de travail</p>
        <nav className="main-nav" aria-label="Navigation principale">
          {NAVIGATION.map((item) => {
            const NavigationIcon = item.icon;
            return (
              <InternalLink
                key={item.to}
                to={item.to}
                className={(isActive) => (isActive ? "nav-link active" : "nav-link")}
                label={sidebarCollapsed ? item.label : undefined}
              >
                <span className="nav-mark" aria-hidden="true">
                  <NavigationIcon />
                </span>
                <span className="nav-label">{item.label}</span>
              </InternalLink>
            );
          })}
        </nav>

        <div className="sidebar-foot">
          <span className="environment-dot" aria-hidden="true" />
          <span>
            {localBypass ? "Environnement local" : user?.full_name}
            <small>{localBypass ? "Services de développement actifs" : user?.email}</small>
          </span>
        </div>
      </aside>

      <main id="main-content" className="main-content" tabIndex={-1}>
        <header className="topbar">
          <div className="topbar-context">
            <button
              className="mobile-menu-button"
              type="button"
              onClick={() => setMobileSidebarOpen(true)}
              aria-label="Ouvrir la navigation"
              aria-expanded={mobileSidebarOpen}
            >
              <Menu aria-hidden="true" />
            </button>
            <span>Plateforme</span>
            <span aria-hidden="true">/</span>
            <strong>{metadata.title}</strong>
          </div>

          <div className="topbar-actions">
            <form className="global-search" role="search" onSubmit={search}>
              <Search aria-hidden="true" />
              <input
                aria-label="Rechercher"
                placeholder="Rechercher…"
                type="search"
                onFocus={() => setCommandOpen(true)}
              />
              <kbd>⌘ K</kbd>
            </form>
            <button
              className="icon-button"
              type="button"
              onClick={toggleTheme}
              aria-label={resolvedTheme === "dark" ? "Activer le mode clair" : "Activer le mode sombre"}
              title={resolvedTheme === "dark" ? "Mode clair" : "Mode sombre"}
            >
              {resolvedTheme === "dark" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
            </button>
            <button className="icon-button" type="button" aria-label="Notifications">
              <Bell aria-hidden="true" />
              <span className="notification-dot" aria-hidden="true" />
            </button>
            <details className="profile-menu">
              <summary className="profile-chip" title={user?.email ?? "Profil local"}>
                <span className="profile-avatar">{initials}</span>
                <span className="profile-copy">
                  <strong>{localBypass ? "Administrateur" : user?.full_name}</strong>
                  <small>{localBypass ? "Mode local" : "Compte actif"}</small>
                </span>
              </summary>
              <div className="profile-menu-card">
                <div className="profile-menu-header">
                  <strong>{localBypass ? "Administrateur local" : user?.full_name}</strong>
                  <small>{localBypass ? "Authentification désactivée en développement" : user?.email}</small>
                </div>
                <button className="profile-menu-action" type="button" onClick={toggleTheme}>
                  {resolvedTheme === "dark" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
                  {resolvedTheme === "dark" ? "Passer en mode clair" : "Passer en mode sombre"}
                </button>
                {!localBypass ? (
                  <button
                    className="profile-menu-action danger"
                    type="button"
                    onClick={() => void logout()}
                  >
                    <LogOut aria-hidden="true" />
                    Se déconnecter
                  </button>
                ) : null}
              </div>
            </details>
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

      {commandOpen ? (
        <div
          className="command-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.currentTarget === event.target) {
              setCommandOpen(false);
            }
          }}
        >
          <section className="command-dialog" role="dialog" aria-modal="true" aria-label="Recherche globale">
            <div className="command-search">
              <Search aria-hidden="true" />
              <input
                autoFocus
                type="search"
                placeholder="Rechercher une page ou une fonction…"
                value={commandQuery}
                onChange={(event) => setCommandQuery(event.target.value)}
              />
              <kbd>Échap</kbd>
            </div>
            <div className="command-results">
              <p className="command-group-label">Navigation PETROLE</p>
              {filteredNavigation.length ? (
                filteredNavigation.map((item) => {
                  const ResultIcon = item.icon;
                  return (
                    <button
                      key={item.to}
                      className="command-item"
                      type="button"
                      onClick={() => choose(item)}
                    >
                      <span className="command-item-icon" aria-hidden="true">
                        <ResultIcon />
                      </span>
                      <span className="command-item-copy">
                        <strong>{item.label}</strong>
                        <small>{item.description}</small>
                      </span>
                    </button>
                  );
                })
              ) : (
                <div className="command-empty">Aucun résultat pour « {commandQuery} ».</div>
              )}
            </div>
            <footer className="command-footer">
              <span>Entrée pour ouvrir</span>
              <span>Ctrl/⌘ + K pour rechercher</span>
            </footer>
          </section>
        </div>
      ) : null}
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
    <section className={`panel ${className}`}>
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
  return <span className={`status-badge ${kind}`}>{value.replaceAll("_", " ")}</span>;
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") || "PT";
}
