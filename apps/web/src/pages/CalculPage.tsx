import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  HydraulicProfileChart,
  NpshChart,
  PressureDistanceChart,
  PumpEfficiencyPowerChart,
} from "../components/charts/HydraulicCharts";
import {
  NumericalSummaryPanel,
  SegmentResultsPanel,
  StationResultsPanel,
} from "../components/results/DetailedResults";
import { apiRequest, downloadApiFile, jsonBody } from "../api";
import { EmptyState, ErrorNotice, Panel, StatusBadge } from "../components/Shell";
import { useNavigation } from "../routing";
import type {
  Calculation,
  CalculationResult,
  ModelVersion,
  Page,
  Project,
  Scenario,
} from "../types";
import { formatNumber } from "../types";

export function CalculPage() {
  const { navigate } = useNavigation();
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [lastCalculation, setLastCalculation] = useState<Calculation | null>(null);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiRequest<Page<Project>>("/projects?limit=200&offset=0"),
  });
  const modelsQuery = useQuery({
    queryKey: ["models", projectId],
    queryFn: () =>
      apiRequest<Page<ModelVersion>>(
        "/projects/" + projectId + "/models?limit=200&offset=0",
      ),
    enabled: Boolean(projectId),
  });
  const scenariosQuery = useQuery({
    queryKey: ["scenarios", modelId],
    queryFn: () =>
      apiRequest<Page<Scenario>>(
        "/models/" + modelId + "/scenarios?limit=200&offset=0",
      ),
    enabled: Boolean(modelId),
  });

  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];
  const scenarios = scenariosQuery.data?.items ?? [];

  useEffect(() => {
    if (!projectId && projects.length) {
      setProjectId(projects[0].id);
    }
  }, [projectId, projects]);

  useEffect(() => {
    if (!models.some((model) => model.id === modelId)) {
      setModelId(models[0]?.id ?? "");
    }
  }, [modelId, models]);

  useEffect(() => {
    if (!scenarios.some((scenario) => scenario.id === scenarioId)) {
      setScenarioId(scenarios[0]?.id ?? "");
    }
  }, [scenarioId, scenarios]);

  useEffect(() => {
    setResult(null);
  }, [scenarioId]);

  const calculationMutation = useMutation({
    mutationFn: async () => {
      const calculation = await apiRequest<Calculation>(
        "/scenarios/" + scenarioId + "/calculations",
        {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID() },
          body: jsonBody({ engine: "long_distance_liquid" }),
        },
      );
      let current = calculation;
      for (let attempt = 0; attempt < 240; attempt += 1) {
        if (!current.status.includes("QUEUED") && !current.status.includes("RUNNING")) {
          break;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 500));
        current = await apiRequest<Calculation>("/calculations/" + calculation.id);
      }
      if (current.status.includes("QUEUED") || current.status.includes("RUNNING")) {
        throw new Error("Le calcul dépasse le délai d'attente de deux minutes.");
      }
      setLastCalculation(current);
      return apiRequest<CalculationResult>("/calculations/" + calculation.id + "/results");
    },
    onSuccess: setResult,
  });

  const exportMutation = useMutation({
    mutationFn: ({
      format,
      section,
    }: {
      format: "xlsx" | "csv" | "json";
      section?: "profile" | "segments" | "stations" | "pumps";
    }) => {
      const calculationId = result?.calculation_id ?? "";
      const query = new URLSearchParams({ format });
      if (section) {
        query.set("section", section);
      }
      const extension = format === "csv" ? `-${section ?? "profil"}.csv` : `.${format}`;
      return downloadApiFile(
        "/calculations/" + calculationId + "/export?" + query.toString(),
        "calcul-" + calculationId.slice(0, 8) + extension,
      );
    },
  });

  const summary = result?.result;
  const runningPumps = (summary?.stations ?? []).flatMap((station) =>
    station.pumps.filter((pump) => pump.running),
  );
  const npshChart = runningPumps.length ? <NpshChart pumps={runningPumps} /> : null;
  const engineVersion = lastCalculation?.engine_version ?? "non publié";
  const inputHash = lastCalculation?.input_hash ?? "non publiée";
  const profile = useMemo(() => summary?.profile ?? [], [summary]);
  const violations = summary?.violations ?? [];
  const warnings = summary?.warnings ?? [];
  const ruleEvaluations = summary?.rule_evaluations ?? [];
  const error =
    projectsQuery.error ??
    modelsQuery.error ??
    scenariosQuery.error ??
    calculationMutation.error;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}

      <Panel
        title="Chaîne de calcul"
        description="Le modèle et le scénario sont figés dans le paquet d'entrée du calcul."
      >
        <div className="form-grid three">
          <label>
            Projet
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
              <option value="">Sélectionner</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.code} — {project.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Version de modèle
            <select
              value={modelId}
              onChange={(event) => setModelId(event.target.value)}
              disabled={!projectId}
            >
              <option value="">Sélectionner</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  V{model.version_number} — {model.name} ({model.status})
                </option>
              ))}
            </select>
          </label>
          <label>
            Scénario
            <select
              value={scenarioId}
              onChange={(event) => setScenarioId(event.target.value)}
              disabled={!modelId}
            >
              <option value="">Sélectionner</option>
              {scenarios.map((scenario) => (
                <option key={scenario.id} value={scenario.id}>
                  {scenario.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="button-row">
          <button
            className="button button-primary"
            disabled={!scenarioId || calculationMutation.isPending}
            onClick={() => calculationMutation.mutate()}
          >
            {calculationMutation.isPending ? "Calcul en cours…" : "Exécuter HydroLiquid Core"}
          </button>
          {result ? <StatusBadge value={result.status} /> : null}
        </div>
      </Panel>

      {!scenarios.length && modelId ? (
        <Panel
          title="Aucun scénario sur cette version"
          description="Les conditions d'étude se saisissent dans un formulaire dédié."
        >
          <EmptyState
            title="Aucun scénario calculable"
            detail="Renseignez les conditions aux limites, l'état des équipements et les options du solveur dans l'écran « Scénarios »."
          />
          <div className="button-row">
            <button
              type="button"
              className="button button-primary"
              onClick={() => navigate("/scenarios")}
            >
              Ouvrir l'écran Scénarios
            </button>
          </div>
        </Panel>
      ) : null}

      {summary ? (
        <>
          <section className="metrics-grid">
            <ResultMetric
              label="Débit"
              value={formatNumber(summary.flow_m3_s * 3600)}
              unit="m³/h"
            />
            <ResultMetric
              label="Pression minimale"
              value={formatNumber(summary.min_pressure_pa / 100000)}
              unit="bar abs."
            />
            <ResultMetric
              label="Perte de charge"
              value={formatNumber(summary.total_head_loss_m)}
              unit="m"
            />
            <ResultMetric
              label="Résidu"
              value={formatNumber(summary.residual, 8)}
              unit=""
            />
          </section>

          <Panel
            title="Éligibilité à la décision"
            description="Le verdict physique reste distinct de la conformité normative."
          >
            <div className="resource-summary">
              <div>
                <span>Contrôles physiques</span>
                <StatusBadge
                  value={summary.physical_approvable ? "approvable" : "bloqué"}
                />
              </div>
              <div>
                <span>Conformité normative</span>
                <StatusBadge value={summary.compliance_status} />
              </div>
              <div>
                <span>Décision positive</span>
                <StatusBadge
                  value={summary.decision_eligible ? "éligible" : "interdite"}
                />
              </div>
            </div>
            {summary.compliance_status === "not_evaluated" ? (
              <div className="notice notice-error" role="alert">
                Aucun jeu de règles approuvé n’a été évalué. Le rapport peut être généré,
                mais son approbation positive reste interdite.
              </div>
            ) : null}
          </Panel>

          <Panel
            title="Profil hydraulique"
            description="Ligne piézométrique et profil du terrain suivant le chaînage."
          >
            <HydraulicProfileChart points={profile} />
          </Panel>

          <Panel
            title="Pression et vitesse"
            description="Pression absolue et vitesse d'écoulement suivant le chaînage."
          >
            <PressureDistanceChart points={profile} />
          </Panel>

          <SegmentResultsPanel segments={summary.segments ?? []} />
          <StationResultsPanel stations={summary.stations ?? []} />

          {runningPumps.length ? (
            <>
              <Panel
                title="Rendement et puissance des pompes"
                description="Point de fonctionnement de chaque pompe en marche."
              >
                <PumpEfficiencyPowerChart pumps={runningPumps} />
              </Panel>
              {npshChart ? (
                <Panel title="NPSH" description="Disponible, requis et marge résultante par pompe.">
                  {npshChart}
                </Panel>
              ) : null}
            </>
          ) : null}

          <Panel
            title="Exports"
            description="Résultats déjà calculés, restitués sans nouvelle exécution."
          >
            <div className="button-row">
              <button
                type="button"
                className="button button-secondary"
                onClick={() => exportMutation.mutate({ format: "xlsx" })}
                disabled={exportMutation.isPending}
              >
                Classeur XLSX
              </button>
              <button
                type="button"
                className="button button-ghost"
                onClick={() => exportMutation.mutate({ format: "json" })}
                disabled={exportMutation.isPending}
              >
                Données JSON
              </button>
              {(["profile", "segments", "stations", "pumps"] as const).map((section) => (
                <button
                  key={section}
                  type="button"
                  className="button button-ghost"
                  onClick={() => exportMutation.mutate({ format: "csv", section })}
                  disabled={exportMutation.isPending}
                >
                  CSV {SECTION_LABELS[section]}
                </button>
              ))}
            </div>
            <p className="field-help">
              Le classeur regroupe le profil, les tronçons, les stations et les pompes. Un
              fichier CSV ne porte qu'un seul tableau à la fois.
            </p>
          </Panel>

          <NumericalSummaryPanel
            summary={summary}
            engineVersion={engineVersion}
            inputHash={inputHash}
          />

          <div className="content-grid equal">
            <Panel title="Contrôles physiques" description="Violations bloquantes.">
              {violations.length ? (
                <ul className="issue-list negative">
                  {violations.map((violation, index) => (
                    <li key={String(violation.code) + index}>
                      <strong>{String(violation.code)}</strong>
                      <span>{String(violation.message)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  title="Aucune violation bloquante"
                  detail="Les limites codées ont été respectées pour ce calcul."
                />
              )}
            </Panel>
            <Panel title="Avertissements" description="Hypothèses ou marges à contrôler.">
              {warnings.length ? (
                <ul className="issue-list">
                  {warnings.map((warning, index) => (
                    <li key={String(warning.code) + index}>
                      <strong>{String(warning.code)}</strong>
                      <span>{String(warning.message)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  title="Aucun avertissement"
                  detail="Le moteur n'a signalé aucune réserve supplémentaire."
                />
              )}
            </Panel>
          </div>

          <Panel
            title="Contrôles normatifs"
            description="Seuils figés dans l’empreinte du calcul."
          >
            {ruleEvaluations.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Règle</th>
                      <th>Sévérité</th>
                      <th>Statut</th>
                      <th>Valeur</th>
                      <th>Limite</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ruleEvaluations.map((evaluation) => (
                      <tr key={evaluation.id}>
                        <td>
                          <strong>{evaluation.rule_code ?? evaluation.rule_id.slice(0, 8)}</strong>
                          <small>{evaluation.message}</small>
                        </td>
                        <td>{evaluation.severity ?? "—"}</td>
                        <td><StatusBadge value={evaluation.status} /></td>
                        <td>{formatOptionalNumber(evaluation.measured_value, evaluation.unit)}</td>
                        <td>{formatOptionalNumber(evaluation.limit_value, evaluation.unit)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="Aucune règle évaluée"
                detail="Sélectionnez un jeu de règles approuvé dans la fiche projet."
              />
            )}
          </Panel>
        </>
      ) : (
        <Panel title="Résultat" description="Synthèse, profil et diagnostics.">
          <EmptyState
            title="Aucun calcul affiché"
            detail="Sélectionnez un scénario puis exécutez le moteur."
          />
        </Panel>
      )}
    </div>
  );
}

function ResultMetric({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <article className="metric-card blue">
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{unit || "sans unité"}</small>
    </article>
  );
}

function formatOptionalNumber(value: number | null, unit: string | null): string {
  return value === null ? "—" : formatNumber(value) + (unit ? " " + unit : "");
}

/** Intitulés courts des sections exportables. */
const SECTION_LABELS: Record<"profile" | "segments" | "stations" | "pumps", string> = {
  profile: "profil",
  segments: "tronçons",
  stations: "stations",
  pumps: "pompes",
};
