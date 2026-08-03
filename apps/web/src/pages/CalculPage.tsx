import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest, jsonBody } from "../api";
import { EmptyState, ErrorNotice, Panel, StatusBadge, SuccessNotice } from "../components/Shell";
import { EXAMPLE_SCENARIO } from "../samples";
import type {
  Calculation,
  CalculationProfilePoint,
  CalculationResult,
  ModelVersion,
  Page,
  Project,
  Scenario,
} from "../types";
import { formatNumber } from "../types";

export function CalculPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [scenarioName, setScenarioName] = useState("Régime nominal");
  const [scenarioPayload, setScenarioPayload] = useState(
    JSON.stringify(EXAMPLE_SCENARIO, null, 2),
  );
  const [result, setResult] = useState<CalculationResult | null>(null);

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

  const scenarioMutation = useMutation({
    mutationFn: () =>
      apiRequest<Scenario>("/models/" + modelId + "/scenarios", {
        method: "POST",
        body: jsonBody({
          name: scenarioName,
          payload: JSON.parse(scenarioPayload) as Record<string, unknown>,
        }),
      }),
    onSuccess: async (scenario) => {
      setScenarioId(scenario.id);
      await queryClient.invalidateQueries({ queryKey: ["scenarios", modelId] });
    },
  });

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
      return apiRequest<CalculationResult>(
        "/calculations/" + calculation.id + "/results",
      );
    },
    onSuccess: setResult,
  });

  const summary = result?.result;
  const profile = useMemo(() => summary?.profile ?? [], [summary]);
  const violations = summary?.violations ?? [];
  const warnings = summary?.warnings ?? [];
  const ruleEvaluations = summary?.rule_evaluations ?? [];
  const error =
    projectsQuery.error ??
    modelsQuery.error ??
    scenariosQuery.error ??
    scenarioMutation.error ??
    calculationMutation.error;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {scenarioMutation.isSuccess ? (
        <SuccessNotice>Le scénario est enregistré et prêt à être calculé.</SuccessNotice>
      ) : null}

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
          title="Créer le scénario initial"
          description="Conditions aux limites, options du solveur et états des équipements."
        >
          <form
            className="editor-form"
            onSubmit={(event) => {
              event.preventDefault();
              scenarioMutation.mutate();
            }}
          >
            <label>
              Nom du scénario
              <input
                value={scenarioName}
                onChange={(event) => setScenarioName(event.target.value)}
                required
              />
            </label>
            <label>
              Paramètres du scénario
              <textarea
                className="code-editor"
                rows={20}
                value={scenarioPayload}
                onChange={(event) => setScenarioPayload(event.target.value)}
                spellCheck={false}
              />
            </label>
            <div className="button-row">
              <button
                className="button button-primary"
                disabled={!modelId || scenarioMutation.isPending}
              >
                Enregistrer le scénario
              </button>
              <button
                type="button"
                className="button button-ghost"
                onClick={() => setScenarioPayload(JSON.stringify(EXAMPLE_SCENARIO, null, 2))}
              >
                Restaurer l'exemple
              </button>
            </div>
          </form>
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
            title="Profil pression–altitude"
            description="Pression absolue et profil altimétrique suivant le chaînage."
          >
            <ProfileChart points={profile} />
          </Panel>

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

function ProfileChart({ points }: { points: CalculationProfilePoint[] }) {
  if (!points.length) {
    return <EmptyState title="Profil vide" detail="Aucun point de profil n'a été produit." />;
  }
  const width = 900;
  const height = 300;
  const padding = 34;
  const chainages = points.map((point) => point.chainage_m);
  const pressures = points.map((point) => point.pressure_pa / 100000);
  const minX = Math.min(...chainages);
  const maxX = Math.max(...chainages);
  const minY = Math.min(...pressures);
  const maxY = Math.max(...pressures);
  const x = (value: number) =>
    padding + ((value - minX) / Math.max(maxX - minX, 1)) * (width - 2 * padding);
  const y = (value: number) =>
    height -
    padding -
    ((value - minY) / Math.max(maxY - minY, 1)) * (height - 2 * padding);
  const polyline = points
    .map((point) => String(x(point.chainage_m)) + "," + String(y(point.pressure_pa / 100000)))
    .join(" ");

  return (
    <div className="chart-wrap">
      <svg
        className="profile-chart"
        viewBox={"0 0 " + width + " " + height}
        role="img"
        aria-label="Profil de pression absolue suivant le chaînage"
      >
        <defs>
          <linearGradient id="pressure-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#18a980" stopOpacity="0.34" />
            <stop offset="100%" stopColor="#18a980" stopOpacity="0" />
          </linearGradient>
        </defs>
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} />
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
        />
        <polygon
          points={
            padding +
            "," +
            (height - padding) +
            " " +
            polyline +
            " " +
            (width - padding) +
            "," +
            (height - padding)
          }
          fill="url(#pressure-fill)"
          stroke="none"
        />
        <polyline points={polyline} fill="none" stroke="#18a980" strokeWidth="3" />
        <text x={padding} y={20}>
          {formatNumber(maxY)} bar
        </text>
        <text x={padding} y={height - 8}>
          {formatNumber(minX / 1000)} km
        </text>
        <text x={width - padding} y={height - 8} textAnchor="end">
          {formatNumber(maxX / 1000)} km
        </text>
      </svg>
    </div>
  );
}

function formatOptionalNumber(value: number | null, unit: string | null): string {
  return value === null ? "—" : formatNumber(value) + (unit ? " " + unit : "");
}
