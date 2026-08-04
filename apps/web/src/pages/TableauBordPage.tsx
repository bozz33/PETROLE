import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";

import { apiRequest } from "@/api";
import { EChart } from "@/components/charts/EChart";
import { EmptyState, ErrorNotice, Panel, StatusBadge } from "@/components/Shell";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { InternalLink } from "@/routing";
import { useTheme } from "@/theme";
import type { Health, Organization, Page, Project, Readiness } from "@/types";
import { formatDate } from "@/types";

export function TableauBordPage() {
  const { resolvedTheme } = useTheme();
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

  const activityOption = useMemo<EChartsOption>(() => {
    const dark = resolvedTheme === "dark";
    const text = dark ? "#9AAEB5" : "#60747C";
    const grid = dark ? "#24414A" : "#D8E1E4";
    const line = dark ? "#2A92A2" : "#0F4C5C";

    return {
      animationDuration: 650,
      backgroundColor: "transparent",
      grid: { left: 42, right: 18, top: 22, bottom: 34 },
      tooltip: {
        trigger: "axis",
        backgroundColor: dark ? "#0D252D" : "#FFFFFF",
        borderColor: grid,
        textStyle: { color: dark ? "#E8F1F3" : "#102A33" },
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
        axisLine: { lineStyle: { color: grid } },
        axisTick: { show: false },
        axisLabel: { color: text },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: text, formatter: "{value}k" },
        splitLine: { lineStyle: { color: grid, type: "dashed" } },
      },
      series: [
        {
          name: "Calculs exécutés",
          type: "line",
          smooth: true,
          symbolSize: 7,
          data: [7.2, 8.5, 7.9, 10.7, 9.8, 12.4, 11.3],
          lineStyle: { width: 3, color: line },
          itemStyle: { color: line, borderColor: dark ? "#0D252D" : "#FFFFFF", borderWidth: 2 },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: dark ? "rgba(42,146,162,.34)" : "rgba(15,76,92,.24)" },
                { offset: 1, color: "rgba(15,76,92,0)" },
              ],
            },
          },
        },
      ],
    };
  }, [resolvedTheme]);

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
                ? `Version ${healthQuery.data.version}`
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
          <EChart
            option={activityOption}
            className="h-[270px]"
            ariaLabel="Activité hydraulique sur sept jours"
          />
        </Panel>

        <Panel title="Répartition des projets" description="État actuel du portefeuille.">
          <div className="distribution-layout">
            <div className="distribution-donut" aria-hidden="true" />
            <div className="distribution-legend">
              <DistributionItem tone="a" label="Projets actifs" value={activeProjects} />
              <DistributionItem tone="b" label="Brouillons" value={draftProjects} />
              <DistributionItem tone="c" label="Archivés" value={archivedProjects} />
              <DistributionItem tone="d" label="Organisations" value={organizations.length} />
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
            detail="Créez une organisation et son premier projet pour commencer la modélisation."
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
