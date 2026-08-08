import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { ScenarioComparisonChart } from "../components/charts/HydraulicCharts";
import { apiRequest, jsonBody } from "../api";
import {
  EmptyState,
  ErrorNotice,
  Panel,
  StatusBadge,
  SuccessNotice,
} from "../components/Shell";
import type {
  AssetInstance,
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
  const [referenceDurationH, setReferenceDurationH] = useState("1");
  const [energyPricePerKwh, setEnergyPricePerKwh] = useState("");
  const [minimumFlowM3H, setMinimumFlowM3H] = useState("");
  const [maximumFlowM3H, setMaximumFlowM3H] = useState("");
  const [minimumPressureBar, setMinimumPressureBar] = useState("");
  const [maximumPressureBar, setMaximumPressureBar] = useState("");
  const [maximumActivePumps, setMaximumActivePumps] = useState("");
  const [requiredPumpIds, setRequiredPumpIds] = useState<string[]>([]);
  const [forbiddenPumpIds, setForbiddenPumpIds] = useState<string[]>([]);
  const [allowViolations, setAllowViolations] = useState(false);
  const [maximumConfigurations, setMaximumConfigurations] = useState("100000");
  const [maximumEvaluations, setMaximumEvaluations] = useState("");
  const [solver, setSolver] = useState<"enumeration" | "pyomo">("enumeration");
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
  const assetsQuery = useQuery({
    queryKey: ["assets", modelId],
    queryFn: () =>
      apiRequest<Page<AssetInstance>>("/models/" + modelId + "/assets?limit=2000&offset=0"),
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
  const pumps = (assetsQuery.data?.items ?? []).filter(
    (asset) => asset.role === "main" || asset.role === "standby",
  );

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
            reference_duration_s: (optionalNumber(referenceDurationH) ?? 1) * 3_600,
            energy_price_per_kwh: optionalNumber(energyPricePerKwh),
            solver,
            maximum_configurations: optionalNumber(maximumConfigurations) ?? 100_000,
            maximum_evaluations: optionalNumber(maximumEvaluations),
            constraints: {
              minimum_flow_m3_s: divide(optionalNumber(minimumFlowM3H), 3_600),
              maximum_flow_m3_s: divide(optionalNumber(maximumFlowM3H), 3_600),
              minimum_pressure_pa: multiply(optionalNumber(minimumPressureBar), 100_000),
              maximum_pressure_pa: multiply(optionalNumber(maximumPressureBar), 100_000),
              maximum_active_pumps: optionalNumber(maximumActivePumps),
              required_pump_ids: requiredPumpIds,
              forbidden_pump_ids: forbiddenPumpIds,
              allow_violations: allowViolations,
            },
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
    assetsQuery.error ??
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
            <>
            <div className="chart-wrap">
              <ScenarioComparisonChart comparison={comparison} />
            </div>
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
            </>
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
                <option value="min_cost">Coût minimal</option>
                <option value="min_pump_count">Nombre de pompes minimal</option>
                <option value="min_starts">Démarrages minimaux</option>
                <option value="max_flow">Débit maximal</option>
              </select>
            </label>
            <label>
              Rapports de vitesse
              <input value={speedOptions} onChange={(event) => setSpeedOptions(event.target.value)} />
              <small>Valeurs séparées par une virgule, par exemple 0,8 et 1,0.</small>
            </label>
            <div className="form-grid">
              <label>
                Durée de référence (h)
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={referenceDurationH}
                  onChange={(event) => setReferenceDurationH(event.target.value)}
                />
              </label>
              <label>
                Prix de l'énergie (€/kWh)
                <input
                  type="number"
                  step="0.001"
                  min="0"
                  value={energyPricePerKwh}
                  onChange={(event) => setEnergyPricePerKwh(event.target.value)}
                />
              </label>
            </div>

            <fieldset className="field-group">
              <legend>Contraintes d'exploitation</legend>
              <div className="form-grid">
                <label>
                  Débit minimal (m³/h)
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={minimumFlowM3H}
                    onChange={(event) => setMinimumFlowM3H(event.target.value)}
                  />
                </label>
                <label>
                  Débit maximal (m³/h)
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={maximumFlowM3H}
                    onChange={(event) => setMaximumFlowM3H(event.target.value)}
                  />
                </label>
                <label>
                  Pression minimale (bar abs.)
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={minimumPressureBar}
                    onChange={(event) => setMinimumPressureBar(event.target.value)}
                  />
                </label>
                <label>
                  Pression maximale (bar abs.)
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={maximumPressureBar}
                    onChange={(event) => setMaximumPressureBar(event.target.value)}
                  />
                </label>
                <label>
                  Pompes actives au maximum
                  <input
                    type="number"
                    step="1"
                    min="0"
                    value={maximumActivePumps}
                    onChange={(event) => setMaximumActivePumps(event.target.value)}
                  />
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={allowViolations}
                    onChange={(event) => setAllowViolations(event.target.checked)}
                  />
                  Conserver les configurations en violation
                </label>
              </div>
            </fieldset>

            {pumps.length ? (
              <fieldset className="field-group">
                <legend>Pompes imposées ou exclues</legend>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Pompe</th>
                        <th>Obligatoire</th>
                        <th>Interdite</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pumps.map((pump) => (
                        <tr key={pump.id}>
                          <td>
                            <strong>{pump.code}</strong>
                            <small>{pump.role === "standby" ? "Secours" : "Principale"}</small>
                          </td>
                          <td>
                            <input
                              type="checkbox"
                              checked={requiredPumpIds.includes(pump.code)}
                              onChange={() => {
                                setRequiredPumpIds((current) => toggle(current, pump.code));
                                setForbiddenPumpIds((current) =>
                                  current.filter((code) => code !== pump.code),
                                );
                              }}
                            />
                          </td>
                          <td>
                            <input
                              type="checkbox"
                              checked={forbiddenPumpIds.includes(pump.code)}
                              onChange={() => {
                                setForbiddenPumpIds((current) => toggle(current, pump.code));
                                setRequiredPumpIds((current) =>
                                  current.filter((code) => code !== pump.code),
                                );
                              }}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </fieldset>
            ) : null}

            <div className="form-grid">
              <label>
                Configurations générées au maximum
                <input
                  type="number"
                  step="1"
                  min="1"
                  value={maximumConfigurations}
                  onChange={(event) => setMaximumConfigurations(event.target.value)}
                />
              </label>
              <label>
                Voie de résolution
                <select
                  value={solver}
                  onChange={(event) => setSolver(event.target.value as "enumeration" | "pyomo")}
                >
                  <option value="enumeration">Énumération filtrée</option>
                  <option value="pyomo">Programmation en nombres entiers (Pyomo)</option>
                </select>
                <small>
                  Les deux voies retiennent le même optimum ; la seconde pose la décision
                  comme un programme explicite.
                </small>
              </label>
              <label>
                Évaluations au maximum
                <input
                  type="number"
                  step="1"
                  min="1"
                  value={maximumEvaluations}
                  onChange={(event) => setMaximumEvaluations(event.target.value)}
                  placeholder="Sans limite"
                />
              </label>
            </div>
            <button className="button button-primary" disabled={!scenarioId || optimizationMutation.isPending}>
              {optimizationMutation.isPending ? "Recherche…" : "Rechercher la configuration"}
            </button>
          </form>
          {optimization ? (
            <div className="report-result">
              <dl className="detail-list">
                <div><dt>Statut</dt><dd><StatusBadge value={optimization.status} /></dd></div>
                <div><dt>Candidats évalués</dt><dd>{optimization.result_payload.evaluated_count} / {optimization.result_payload.generated_count}</dd></div>
                <div>
                  <dt>Espace exploré</dt>
                  <dd>{optimization.result_payload.complete ? "Complet" : "Tronqué par les bornes"}</dd>
                </div>
                <div>
                  <dt>Écart d'optimalité</dt>
                  <dd>
                    {optimization.result_payload.optimality_gap === null
                      ? "—"
                      : formatNumber(optimization.result_payload.optimality_gap)}
                  </dd>
                </div>
                <div><dt>Configurations rejetées</dt><dd>{optimization.result_payload.rejected.length}</dd></div>
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
                <EmptyState
                  title="Aucune solution faisable"
                  detail="Aucune configuration ne satisfait les contraintes retenues."
                />
              )}
              {optimization.result_payload.rejected.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Configuration rejetée</th>
                        <th>Motif</th>
                      </tr>
                    </thead>
                    <tbody>
                      {optimization.result_payload.rejected.slice(0, 20).map((entry, index) => (
                        <tr key={rejectionConfigurationId(entry) + String(index)}>
                          <td className="mono">{rejectionConfigurationId(entry)}</td>
                          <td>{describeRejection(entry)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {optimization.result_payload.rejected.length > 20 ? (
                    <p className="field-help">
                      {optimization.result_payload.rejected.length - 20} autres rejets non affichés.
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : (
            <EmptyState title="Aucune recherche" detail="Le scénario doit contenir au moins une pompe." />
          )}
        </Panel>
      </div>
    </div>
  );
}

function optionalNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function divide(value: number | null, factor: number): number | null {
  return value === null ? null : value / factor;
}

function multiply(value: number | null, factor: number): number | null {
  return value === null ? null : value * factor;
}

function toggle(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

/** Rend lisible le motif de rejet renvoyé par l'optimiseur. */
export function describeRejection(entry: Record<string, unknown>): string {
  const reasons = entry.reasons;
  if (Array.isArray(reasons) && reasons.length) {
    return reasons.map(String).join(" ; ");
  }
  return "Motif non renseigné par le moteur";
}

/** Identifiant lisible d'une configuration rejetée. */
export function rejectionConfigurationId(entry: Record<string, unknown>): string {
  const configuration = entry.configuration;
  if (configuration && typeof configuration === "object") {
    const identifier = (configuration as Record<string, unknown>).id;
    if (typeof identifier === "string") {
      return identifier;
    }
  }
  return "—";
}
