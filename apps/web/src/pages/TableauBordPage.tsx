import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "../api";
import { EmptyState, ErrorNotice, Panel, StatusBadge } from "../components/Shell";
import { InternalLink } from "../routing";
import type { Health, Organization, Page, Project, Readiness } from "../types";
import { formatDate } from "../types";

export function TableauBordPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: () => apiRequest<Health>("/health"),
    refetchInterval: 30_000,
  });
  const readinessQuery = useQuery({
    queryKey: ["readiness"],
    queryFn: () => apiRequest<Readiness>("/health/ready"),
    refetchInterval: 30_000,
  });
  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<Page<Organization>>("/organizations?limit=200&offset=0"),
  });
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiRequest<Page<Project>>("/projects?limit=200&offset=0"),
  });

  const organizations = organizationsQuery.data?.items ?? [];
  const projects = projectsQuery.data?.items ?? [];
  const activeProjects = projects.filter((project) => project.status === "active").length;
  const draftProjects = projects.filter((project) => project.status === "draft").length;
  const loading =
    healthQuery.isLoading ||
    readinessQuery.isLoading ||
    organizationsQuery.isLoading ||
    projectsQuery.isLoading;
  const error =
    healthQuery.error ??
    readinessQuery.error ??
    organizationsQuery.error ??
    projectsQuery.error;

  if (error) {
    return <ErrorNotice error={error} />;
  }

  return (
    <div className="stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">MVP liquide en régime permanent</p>
          <h2>Décider avec un calcul traçable.</h2>
          <p>
            Préparez le modèle, contrôlez les données, exécutez le moteur puis figez une
            note de calcul reproductible.
          </p>
          <div className="button-row">
            <InternalLink className="button button-primary" to="/calcul">
              Lancer un calcul
            </InternalLink>
            <InternalLink className="button button-ghost" to="/donnees">
              Importer des données
            </InternalLink>
          </div>
        </div>
        <div className="hero-orbit" aria-hidden="true">
          <span className="orbit-line" />
          <span className="orbit-node node-a" />
          <span className="orbit-node node-b" />
          <span className="orbit-node node-c" />
          <strong>ΔP</strong>
        </div>
      </section>

      <section className="metrics-grid" aria-label="Indicateurs">
        <Metric
          label="État de l'API"
          value={loading ? "…" : readinessQuery.data?.status ?? "indisponible"}
          detail={
            readinessQuery.data
              ? "Base et stockage objet disponibles"
              : healthQuery.data?.version
                ? "Version " + healthQuery.data.version
                : "Vérification en cours"
          }
          tone="green"
        />
        <Metric
          label="Organisations"
          value={loading ? "…" : String(organizations.length)}
          detail="Espaces de données isolés"
          tone="blue"
        />
        <Metric
          label="Projets actifs"
          value={loading ? "…" : String(activeProjects)}
          detail={String(draftProjects) + " brouillon(s)"}
          tone="amber"
        />
        <Metric
          label="Validation"
          value="14 / 14"
          detail="Cas analytiques rapides"
          tone="purple"
        />
      </section>

      <div className="content-grid two-thirds">
        <Panel
          title="Projets récents"
          description="Derniers référentiels modifiés."
          action={
            <InternalLink className="text-link" to="/projets">
              Voir tous
            </InternalLink>
          }
        >
          {projects.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Projet</th>
                    <th>Code</th>
                    <th>Statut</th>
                    <th>Modification</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.slice(0, 6).map((project) => (
                    <tr key={project.id}>
                      <td>
                        <strong>{project.name}</strong>
                        <small>{project.country_code?.toUpperCase() ?? "Pays non défini"}</small>
                      </td>
                      <td className="mono">{project.code}</td>
                      <td>
                        <StatusBadge value={project.status} />
                      </td>
                      <td>{formatDate(project.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="Aucun projet"
              detail="Créez une organisation et son premier projet pour démarrer."
            />
          )}
        </Panel>

        <Panel title="Parcours recommandé" description="Verticale de calcul contrôlée.">
          <ol className="steps-list">
            <Step number="1" title="Référentiel" detail="Projet et version de modèle." />
            <Step number="2" title="Données" detail="Profil, courbes et unités validés." />
            <Step number="3" title="Scénario" detail="Conditions aux limites explicites." />
            <Step number="4" title="Calcul" detail="Résidus et contrôles physiques." />
            <Step number="5" title="Rapport" detail="PDF figé, haché et approuvé." />
          </ol>
        </Panel>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "green" | "blue" | "amber" | "purple";
}) {
  return (
    <article className={"metric-card " + tone}>
      <span className="metric-pulse" />
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function Step({
  number,
  title,
  detail,
}: {
  number: string;
  title: string;
  detail: string;
}) {
  return (
    <li>
      <span>{number}</span>
      <div>
        <strong>{title}</strong>
        <small>{detail}</small>
      </div>
    </li>
  );
}
