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
  const archivedProjects = projects.filter((project) => project.status === "archived").length;
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
      <section className="metrics-grid" aria-label="Indicateurs principaux">
        <Metric
          label="Disponibilité plateforme"
          value={loading ? "…" : readinessQuery.data?.status === "ready" ? "100 %" : "À vérifier"}
          detail={
            readinessQuery.data
              ? "Base et stockage objet accessibles"
              : healthQuery.data?.version
                ? "Version " + healthQuery.data.version
                : "Vérification en cours"
          }
          trend="Services opérationnels"
          tone="green"
          icon="availability"
        />
        <Metric
          label="Organisations"
          value={loading ? "…" : String(organizations.length)}
          detail="Espaces de données isolés"
          trend="Multi-tenant actif"
          tone="blue"
          icon="organizations"
        />
        <Metric
          label="Projets actifs"
          value={loading ? "…" : String(activeProjects)}
          detail={`${draftProjects} brouillon(s)`}
          trend="Suivi des études"
          tone="amber"
          icon="projects"
        />
        <Metric
          label="Validation scientifique"
          value="14 / 14"
          detail="Cas analytiques rapides"
          trend="Dossier de preuve disponible"
          tone="purple"
          icon="validation"
        />
      </section>

      <div className="dashboard-grid">
        <Panel
          title="Activité hydraulique"
          description="Évolution indicative des exécutions sur les sept derniers jours."
          action={
            <div className="chart-toolbar">
              <select aria-label="Période du graphique" defaultValue="7">
                <option value="7">7 derniers jours</option>
                <option value="30">30 derniers jours</option>
              </select>
            </div>
          }
        >
          <HydraulicActivityChart />
        </Panel>

        <Panel title="Répartition des projets" description="État actuel du portefeuille.">
          <div className="distribution-layout">
            <div className="distribution-donut" aria-hidden="true" />
            <div className="distribution-legend">
              <DistributionItem tone="a" label="Projets actifs" value={activeProjects} />
              <DistributionItem tone="b" label="Brouillons" value={draftProjects} />
              <DistributionItem tone="c" label="Archivés" value={archivedProjects} />
              <DistributionItem
                tone="d"
                label="Organisations"
                value={organizations.length}
              />
            </div>
          </div>
        </Panel>
      </div>

      <Panel
        title="Projets récents"
        description="Derniers référentiels modifiés et état de validation."
        action={
          <InternalLink className="text-link" to="/projets">
            Voir tous les projets
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
                  <th>Pays</th>
                  <th>Statut</th>
                  <th>Dernière modification</th>
                </tr>
              </thead>
              <tbody>
                {projects.slice(0, 6).map((project) => (
                  <tr key={project.id}>
                    <td>
                      <strong>{project.name}</strong>
                      <small>{project.project_type.replaceAll("_", " ")}</small>
                    </td>
                    <td className="mono">{project.code}</td>
                    <td>{project.country_code?.toUpperCase() ?? "Non défini"}</td>
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
            detail="Créez une organisation et son premier projet pour commencer la modélisation."
          />
        )}
      </Panel>

      <div className="dashboard-actions">
        <div>
          <InternalLink className="button button-primary" to="/projets">
            + Nouveau projet
          </InternalLink>
          <InternalLink className="button button-secondary" to="/donnees">
            Importer des données
          </InternalLink>
        </div>
        <InternalLink className="button button-warning" to="/calcul">
          Lancer un calcul hydraulique →
        </InternalLink>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
  trend,
  tone,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  trend: string;
  tone: "green" | "blue" | "amber" | "purple";
  icon: "availability" | "organizations" | "projects" | "validation";
}) {
  return (
    <article className={`metric-card ${tone}`}>
      <span className="metric-icon" aria-hidden="true">
        <MetricIcon name={icon} />
      </span>
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{detail}</small>
      <span className={`metric-trend ${tone === "amber" ? "warning" : "positive"}`}>
        {trend}
      </span>
    </article>
  );
}

function DistributionItem({
  tone,
  label,
  value,
}: {
  tone: "a" | "b" | "c" | "d";
  label: string;
  value: number;
}) {
  return (
    <div className="distribution-item">
      <span className={`legend-dot ${tone}`} aria-hidden="true" />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function HydraulicActivityChart() {
  const points = "36,174 105,153 174,165 243,119 312,132 381,88 450,105 519,54 588,76 657,45";
  const area = `36,205 ${points} 657,205`;

  return (
    <div className="dashboard-chart" role="img" aria-label="Courbe d'activité hydraulique sur sept jours">
      <svg viewBox="0 0 700 235" preserveAspectRatio="none">
        {[45, 85, 125, 165, 205].map((y, index) => (
          <g key={y}>
            <line className="chart-grid-line" x1="36" y1={y} x2="675" y2={y} />
            <text className="chart-axis-label" x="4" y={y + 4}>
              {14 - index * 3}k
            </text>
          </g>
        ))}
        <polygon className="chart-area" points={area} />
        <polyline className="chart-line" points={points} />
        {points.split(" ").map((point) => {
          const [x, y] = point.split(",").map(Number);
          return <circle key={point} className="chart-dot" cx={x} cy={y} r="4" />;
        })}
        {[
          [36, "Lun"],
          [140, "Mar"],
          [244, "Mer"],
          [348, "Jeu"],
          [452, "Ven"],
          [556, "Sam"],
          [657, "Dim"],
        ].map(([x, label]) => (
          <text key={String(label)} className="chart-axis-label" x={Number(x)} y="225" textAnchor="middle">
            {label}
          </text>
        ))}
      </svg>
    </div>
  );
}

function MetricIcon({
  name,
}: {
  name: "availability" | "organizations" | "projects" | "validation";
}) {
  const paths = {
    availability: <><path d="M20 11a8 8 0 1 1-3-6.2"/><path d="m20 4-8.5 8.5L8 9"/></>,
    organizations: <><circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20a5 5 0 0 1 10 0M13 20a4 4 0 0 1 8 0"/></>,
    projects: <><path d="M3 7.5h6l2 2h10v8.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 7.5V6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v1.5"/></>,
    validation: <><path d="M12 3 4 6v6c0 5 3.4 8.3 8 9 4.6-.7 8-4 8-9V6z"/><path d="m8.5 12 2.3 2.3 4.8-5"/></>,
  };

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
}
