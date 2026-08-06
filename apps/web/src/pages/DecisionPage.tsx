import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { apiRequest, jsonBody } from "../api";
import {
  EmptyState,
  ErrorNotice,
  Panel,
  StatusBadge,
  SuccessNotice,
} from "../components/Shell";
import type {
  Comparison,
  Calculation,
  ModelVersion,
  Optimization,
  Page,
  Project,
  Scenario,
} from "../types";
import { formatNumber } from "../types";

export function DecisionPage() {
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [calculationIds, setCalculationIds] = useState<string[]>([]);
  const [objective, setObjective] = useState("min_energy");
  const [speedOptions, setSpeedOptions] = useState("0.8, 1.0");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [optimization, setOptimization] = useState<Optimization | null>(null);

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
  const calculationsQuery = useQuery({
    queryKey: ["calculations", scenarioId],
    queryFn: () =>
      apiRequest<Page<Calculation>>(
        "/scenarios/" + scenarioId + "/calculations?limit=200&offset=0",
      ),
    enabled: Boolean(scenarioId),
  });

  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];
  const scenarios = scenariosQuery.data?.items ?? [];
  const calculations = calculationsQuery.data?.items ?? [];

  useEffect(() => {
    if (!projects.some((project) => project.id === projectId)) {
      setProjectId(projects[0]?.id ?? "");
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
    setCalculationIds((selected) => selected.filter((id) => calculations.some((item) => item.id === id)));
  }, [calculations]);

  const comparisonMutation = useMutation({
    mutationFn: () =>
      apiRequest<Comparison>("/projects/" + projectId + "/comparisons", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: jsonBody({ calculation_ids: calculationIds }),
      }),
    onSuccess: setComparison,
  });

  const optimizationMutation = useMutation({
    mutationFn: () =>
      apiRequest<Optimization>(
        "/scenarios/" + scenarioId + "/optimizations",
        {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID() },
          body: jsonBody({
            objective,
            speed_options: speedOptions
              .split(/[\s,;]+/)
              .map(Number)
              .filter((value) => Number.isFinite(value) && value > 0),
            reference_duration_s: 3_600,
            constraints: {},
          }),
        },
      ),
    onSuccess: setOptimization,
  });

  const error =
    projectsQuery.error ??
    modelsQuery.error ??
    scenariosQuery.error ??
    calculationsQuery.error ??
    comparisonMutation.error ??
    optimizationMutation.error;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {comparisonMutation.isSuccess || optimizationMutation.isSuccess ? (
        <SuccessNotice>Le résultat a été calculé, haché et archivé.</SuccessNotice>
      ) : null}

      <Panel
        title="Contexte de décision"
        description="Sélectionnez le projet et le scénario de référence."
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
            Version
            <select value={modelId} onChange={(event) => setModelId(event.target.value)} disabled={!projectId}>
              <option value="">Sélectionner</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  V{model.version_number} — {model.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Scénario à optimiser
            <select value={scenarioId} onChange={(event) => setScenarioId(event.target.value)} disabled={!modelId}>
              <option value="">Sélectionner</option>
              {scenarios.map((scenario) => (
                <option key={scenario.id} value={scenario.id}>{scenario.name}</option>
              ))}
            </select>
          </label>
        </div>
      </Panel>

      <div className="content-grid equal">
        <Panel
          title="Comparer des calculs"
          description="Classement par faisabilité puis puissance absorbée."
        >
          <form
            className="compact-form"
            onSubmit={(event) => {
              event.preventDefault();
              comparisonMutation.mutate();
            }}
          >
            <fieldset className="selection-fieldset">
              <legend>Calculs convergés du scénario sélectionné</legend>
              {calculations.length ? calculations.map((calculation) => (
                <label className="selection-option" key={calculation.id}>
                  <input
                    type="checkbox"
                    checked={calculationIds.includes(calculation.id)}
                    onChange={() =>
                      setCalculationIds((selected) =>
                        selected.includes(calculation.id)
                          ? selected.filter((id) => id !== calculation.id)
                          : [...selected, calculation.id],
                      )
                    }
                  />
                  <span><strong>{calculation.engine}</strong><small>{calculation.status} · {calculation.created_at}</small></span>
                </label>
              )) : <p className="field-help">Exécutez au moins deux calculs avant comparaison.</p>}
            </fieldset>
            <button className="button button-primary" disabled={!projectId || calculationIds.length < 2 || comparisonMutation.isPending}>
              Comparer et archiver
            </button>
          </form>
          {comparison ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Rang</th><th>Calcul</th><th>Débit</th><th>Puissance</th><th>Statut</th></tr>
                </thead>
                <tbody>
                  {comparison.result_payload.ranked.map((item) => (
                    <tr key={item.calculation_id}>
                      <td>{item.rank}</td>
                      <td className="mono">{item.calculation_id.slice(0, 8)}</td>
                      <td>{item.flow_m3_s === null ? "—" : formatNumber(item.flow_m3_s * 3_600) + " m³/h"}</td>
                      <td>{item.total_power_w === null ? "—" : formatNumber(item.total_power_w / 1_000) + " kW"}</td>
                      <td><StatusBadge value={item.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="Aucune comparaison" detail="Sélectionnez au moins deux calculs convergés pour créer un classement." />
          )}
        </Panel>

        <Panel
          title="Optimiser les pompes"
          description="Énumération déterministe de toutes les combinaisons et vitesses."
        >
          <form
            className="compact-form"
            onSubmit={(event) => {
              event.preventDefault();
              optimizationMutation.mutate();
            }}
          >
            <label>
              Objectif
              <select value={objective} onChange={(event) => setObjective(event.target.value)}>
                <option value="min_energy">Énergie minimale</option>
                <option value="min_pump_count">Nombre de pompes minimal</option>
                <option value="min_starts">Démarrages minimaux</option>
                <option value="max_flow">Débit maximal</option>
              </select>
            </label>
            <label>
              Rapports de vitesse
              <input value={speedOptions} onChange={(event) => setSpeedOptions(event.target.value)} />
            </label>
            <button className="button button-primary" disabled={!scenarioId || optimizationMutation.isPending}>
              {optimizationMutation.isPending ? "Recherche…" : "Rechercher la configuration"}
            </button>
          </form>
          {optimization ? (
            <div className="report-result">
              <dl className="detail-list">
                <div><dt>Statut</dt><dd><StatusBadge value={optimization.status} /></dd></div>
                <div><dt>Candidats évalués</dt><dd>{optimization.result_payload.evaluated_count} / {optimization.result_payload.generated_count}</dd></div>
                <div><dt>Moteur</dt><dd>{optimization.engine_version}</dd></div>
              </dl>
              {optimization.result_payload.best ? (
                <div className="optimization-best">
                  <p className="eyebrow">Configuration recommandée</p>
                  <h3>{optimization.result_payload.best.configuration.id}</h3>
                  <p>
                    {formatNumber(optimization.result_payload.best.evaluation.flow_m3_s * 3_600)} m³/h
                    {" · "}
                    {optimization.result_payload.best.evaluation.energy_kwh === null
                      ? "énergie non disponible"
                      : formatNumber(optimization.result_payload.best.evaluation.energy_kwh) + " kWh"}
                  </p>
                </div>
              ) : (
                <EmptyState title="Aucune solution faisable" detail="Consultez les configurations rejetées dans le résultat API." />
              )}
            </div>
          ) : (
            <EmptyState title="Aucune recherche" detail="Le scénario doit contenir au moins une pompe." />
          )}
        </Panel>
      </div>
    </div>
  );
}
