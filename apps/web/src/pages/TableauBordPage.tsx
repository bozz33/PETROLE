import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/api";
import { EmptyState, ErrorNotice, Panel, StatusBadge } from "@/components/Shell";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { InternalLink } from "@/routing";
import type {
  Health,
  Organization,
  Page,
  Project,
  Readiness,
  ScientificValidation,
} from "@/types";
import { formatDate } from "@/types";

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
  const validationQuery = useQuery({
    queryKey: ["scientific-validation"],
    queryFn: () => apiRequest<ScientificValidation>("/health/validation"),
  });

  const organizations = organizationsQuery.data?.items ?? [];
  const projects = projectsQuery.data?.items ?? [];
  const activeProjects = projects.filter((project) => project.status === "active").length;
  const draftProjects = projects.filter((project) => project.status === "draft").length;
  const archivedProjects = projects.filter((project) => project.status === "archived").length;
  const singleOrganization = healthQuery.data?.deployment.mode === "single_org";
  const organization = organizations[0];
  const loading =
    healthQuery.isLoading ||
    readinessQuery.isLoading ||
    organizationsQuery.isLoading ||
    projectsQuery.isLoading ||
    validationQuery.isLoading;
  const error =
    healthQuery.error ??
    readinessQuery.error ??
    organizationsQuery.error ??
    projectsQuery.error ??
    validationQuery.error;

  if (error) {
    return <ErrorNotice error={error} />;
  }

  return (
    <div className="stack">
      <section className="metrics-grid" aria-label="Indicateurs principaux">
        <Metric
          label="État plateforme"
          value={loading ? "…" : readinessQuery.data?.status === "ready" ? "Opérationnel" : "À vérifier"}
          detail={
            readinessQuery.data
              ? "Base prête · stockage prêt"
              : healthQuery.data?.version
                ? `Version ${healthQuery.data.version}`
                : "Vérification en cours"
          }
          trend="État actuel"
          tone="green"
          icon="availability"
        />
        <Metric
          label={singleOrganization ? "Exploitant" : "Organisations"}
          value={loading ? "…" : singleOrganization ? (organization?.name ?? "Non initialisé") : String(organizations.length)}
          detail={singleOrganization ? "Données isolées" : "Espaces de données isolés"}
          trend={singleOrganization ? "Espace de travail" : "Isolation logique"}
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
          value={
            validationQuery.data
              ? `${validationQuery.data.passed} / ${validationQuery.data.total}`
              : "Non publiée"
          }
          detail={
            validationQuery.data
              ? `Qualification ${validationQuery.data.executed_at.slice(0, 10)}`
              : "Aucune preuve publiée avec cette image"
          }
          trend={
            validationQuery.data
              ? `Preuve ${validationQuery.data.proof_hash.slice(0, 12)}`
              : "Validation requise"
          }
          tone="purple"
          icon="validation"
        />
      </section>

      <div className="dashboard-grid">
        <Panel title="Activité hydraulique" description="Historique d'exécution du moteur.">
          <EmptyState
            title="Historique non connecté"
            detail="Aucune donnée de démonstration n'est affichée. Connectez l'agrégation des calculs avant d'afficher une série."
          />
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
                label={singleOrganization ? "Espace de travail" : "Organisations"}
                value={singleOrganization ? Number(Boolean(organization)) : organizations.length}
              />
            </div>
          </div>
        </Panel>
      </div>

      <Panel
        title="Projets récents"
        description="Derniers référentiels modifiés et état de validation."
        action={
          <InternalLink className={buttonVariants({ variant: "link", size: "sm" })} to="/projets">
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
            detail="Créez le premier projet pour commencer la modélisation."
          />
        )}
      </Panel>

      <div className="dashboard-actions">
        <div>
          <InternalLink className={buttonVariants()} to="/projets">
            + Nouveau projet
          </InternalLink>
          <InternalLink className={buttonVariants({ variant: "outline" })} to="/donnees">
            Importer des données
          </InternalLink>
          <InternalLink className={buttonVariants({ variant: "secondary" })} to="/reseau">
            Visualiser le réseau
          </InternalLink>
        </div>
        <InternalLink className={buttonVariants({ variant: "amber" })} to="/calcul">
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
    <Card className={cn("metric-card gap-0 py-0", tone)}>
      <span className="metric-icon" aria-hidden="true">
        <MetricIcon name={icon} />
      </span>
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{detail}</small>
      <span className={`metric-trend ${tone === "amber" ? "warning" : "positive"}`}>
        {trend}
      </span>
    </Card>
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

function MetricIcon({
  name,
}: {
  name: "availability" | "organizations" | "projects" | "validation";
}) {
  const paths = {
    availability: (
      <>
        <path d="M20 11a8 8 0 1 1-3-6.2" />
        <path d="m20 4-8.5 8.5L8 9" />
      </>
    ),
    organizations: (
      <>
        <circle cx="8" cy="8" r="3" />
        <circle cx="17" cy="9" r="2.5" />
        <path d="M3 20a5 5 0 0 1 10 0M13 20a4 4 0 0 1 8 0" />
      </>
    ),
    projects: (
      <>
        <path d="M3 7.5h6l2 2h10v8.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <path d="M3 7.5V6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v1.5" />
      </>
    ),
    validation: (
      <>
        <path d="M12 3 4 6v6c0 5 3.4 8.3 8 9 4.6-.7 8-4 8-9V6z" />
        <path d="m8.5 12 2.3 2.3 4.8-5" />
      </>
    ),
  };

  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}
