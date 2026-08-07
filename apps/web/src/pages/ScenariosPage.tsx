import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest, jsonBody } from "../api";
import { EmptyState, ErrorNotice, Panel, SuccessNotice } from "../components/Shell";
import type {
  AssetInstance,
  ModelVersion,
  NetworkEdge,
  NetworkNode,
  Page,
  Project,
  Scenario,
  ScenarioObjective,
  ScenarioPayload,
  SegmentOverride,
  PumpOverride,
  StationOverride,
} from "../types";

/** Conditions d'étude par défaut, alignées sur les valeurs du solveur. */
const DEFAULT_PAYLOAD: ScenarioPayload = {
  temperature_k: null,
  imposed_flow_m3_s: null,
  inlet_pressure_pa: null,
  outlet_pressure_pa: null,
  inlet_tank_level_m: null,
  outlet_tank_level_m: null,
  pump_overrides: [],
  station_overrides: [],
  segment_overrides: [],
  solver: {
    friction_model: "colebrook_white",
    pressure_tolerance_pa: 1,
    flow_tolerance_m3_s: 1e-9,
    mass_balance_tolerance: 1e-6,
    max_iterations: 100,
    profile_step_m: 1000,
    store_iterations: false,
    use_quadratic_pump_fit: false,
    max_flow_m3_s: null,
    detect_gravity_zones: true,
    apply_gravity_model: false,
    min_velocity_m_s: null,
    max_velocity_m_s: null,
  },
  objective: null,
  energy_price_per_joule: null,
};

const FRICTION_MODELS: { value: ScenarioPayload["solver"]["friction_model"]; label: string }[] = [
  { value: "colebrook_white", label: "Colebrook-White (implicite)" },
  { value: "haaland", label: "Haaland (explicite)" },
  { value: "swamee_jain", label: "Swamee-Jain (explicite)" },
  { value: "altshul", label: "Altshoul" },
];

const OBJECTIVES: { value: ScenarioObjective; label: string }[] = [
  { value: "min_energy", label: "Minimiser l'énergie" },
  { value: "min_cost", label: "Minimiser le coût" },
  { value: "min_pump_count", label: "Minimiser le nombre de pompes" },
  { value: "min_starts", label: "Minimiser les démarrages" },
  { value: "max_flow", label: "Maximiser le débit" },
];

const EQUIPMENT_STATUSES: { value: string; label: string }[] = [
  { value: "", label: "Inchangé (état du modèle)" },
  { value: "available", label: "Disponible" },
  { value: "unavailable", label: "Indisponible" },
  { value: "maintenance", label: "En maintenance" },
  { value: "bypassed", label: "Contourné" },
];

export function ScenariosPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");
  const [name, setName] = useState("Régime nominal");
  const [description, setDescription] = useState("");
  const [payload, setPayload] = useState<ScenarioPayload>(DEFAULT_PAYLOAD);
  const [showCanonical, setShowCanonical] = useState(false);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiRequest<Page<Project>>("/projects?limit=200&offset=0"),
  });
  const modelsQuery = useQuery({
    queryKey: ["models", projectId],
    queryFn: () =>
      apiRequest<Page<ModelVersion>>("/projects/" + projectId + "/models?limit=200&offset=0"),
    enabled: Boolean(projectId),
  });
  const scenariosQuery = useQuery({
    queryKey: ["scenarios", modelId],
    queryFn: () =>
      apiRequest<Page<Scenario>>("/models/" + modelId + "/scenarios?limit=200&offset=0"),
    enabled: Boolean(modelId),
  });
  const nodesQuery = useQuery({
    queryKey: ["nodes", modelId],
    queryFn: () => apiRequest<Page<NetworkNode>>("/models/" + modelId + "/nodes?limit=1000&offset=0"),
    enabled: Boolean(modelId),
  });
  const edgesQuery = useQuery({
    queryKey: ["edges", modelId],
    queryFn: () => apiRequest<Page<NetworkEdge>>("/models/" + modelId + "/edges?limit=2000&offset=0"),
    enabled: Boolean(modelId),
  });
  const assetsQuery = useQuery({
    queryKey: ["assets", modelId],
    queryFn: () =>
      apiRequest<Page<AssetInstance>>("/models/" + modelId + "/assets?limit=2000&offset=0"),
    enabled: Boolean(modelId),
  });

  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];
  const scenarios = scenariosQuery.data?.items ?? [];
  const nodes = useMemo(() => nodesQuery.data?.items ?? [], [nodesQuery.data]);
  const edges = useMemo(() => edgesQuery.data?.items ?? [], [edgesQuery.data]);
  const assets = useMemo(() => assetsQuery.data?.items ?? [], [assetsQuery.data]);

  const stations = useMemo(() => nodes.filter((node) => node.kind === "station"), [nodes]);
  const tanks = useMemo(() => nodes.filter((node) => node.kind === "tank"), [nodes]);
  const pumps = useMemo(
    () => assets.filter((asset) => asset.role === "main" || asset.role === "standby"),
    [assets],
  );

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

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<Scenario>("/models/" + modelId + "/scenarios", {
        method: "POST",
        body: jsonBody({
          name,
          description: description.trim() ? description.trim() : null,
          payload: payload as unknown as Record<string, unknown>,
        }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["scenarios", modelId] });
    },
  });

  const boundary = describeBoundaryConditions(payload, tanks.length > 0);
  const error =
    projectsQuery.error ?? modelsQuery.error ?? scenariosQuery.error ?? createMutation.error;

  const update = <K extends keyof ScenarioPayload>(key: K, value: ScenarioPayload[K]) => {
    setPayload((current) => ({ ...current, [key]: value }));
  };
  const updateSolver = <K extends keyof ScenarioPayload["solver"]>(
    key: K,
    value: ScenarioPayload["solver"][K],
  ) => {
    setPayload((current) => ({ ...current, solver: { ...current.solver, [key]: value } }));
  };

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {createMutation.isSuccess ? (
        <SuccessNotice>
          Le scénario est enregistré. Lancez-le depuis « Calcul hydraulique ».
        </SuccessNotice>
      ) : null}

      <Panel
        title="Version de modèle"
        description="Un scénario s'applique à une version de modèle figée."
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
            Scénarios enregistrés
            <input value={String(scenarios.length)} readOnly tabIndex={-1} />
          </label>
        </div>
      </Panel>

      {!modelId ? (
        <Panel title="Scénario" description="Conditions d'étude transmises au moteur.">
          <EmptyState
            title="Aucune version de modèle sélectionnée"
            detail="Choisissez un projet puis une version de modèle pour préparer un scénario."
          />
        </Panel>
      ) : (
        <form
          className="stack"
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate();
          }}
        >
          <Panel title="Identification" description="Nom et intention de l'étude.">
            <div className="form-grid two">
              <label>
                Nom du scénario
                <input value={name} onChange={(event) => setName(event.target.value)} required />
              </label>
              <label>
                Description
                <input
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Objet de l'étude, hypothèses retenues"
                />
              </label>
            </div>
          </Panel>

          <Panel
            title="Produit et conditions aux limites"
            description="Le moteur exige exactement deux conditions indépendantes."
          >
            <div className="form-grid three">
              <label>
                Température du produit (°C)
                <input
                  type="number"
                  step="0.1"
                  value={kelvinToCelsiusInput(payload.temperature_k)}
                  onChange={(event) =>
                    update("temperature_k", celsiusInputToKelvin(event.target.value))
                  }
                  placeholder="Température de référence du fluide"
                />
                <small>Laisser vide pour utiliser la température de référence du produit.</small>
              </label>
              <label>
                Débit imposé (m³/h)
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={numberInput(scale(payload.imposed_flow_m3_s, 3600))}
                  onChange={(event) =>
                    update("imposed_flow_m3_s", unscale(parseOptionalNumber(event.target.value), 3600))
                  }
                  placeholder="Vide : débit recherché par le solveur"
                />
                <small>Vide, le débit devient l'inconnue du problème.</small>
              </label>
              <label>
                Objectif d'exploitation
                <select
                  value={payload.objective ?? ""}
                  onChange={(event) =>
                    update("objective", (event.target.value || null) as ScenarioObjective | null)
                  }
                >
                  <option value="">Aucun</option>
                  {OBJECTIVES.map((objective) => (
                    <option key={objective.value} value={objective.value}>
                      {objective.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="form-grid two">
              <fieldset className="field-group">
                <legend>Condition amont</legend>
                <label>
                  Pression d'entrée (bar abs.)
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={numberInput(scale(payload.inlet_pressure_pa, 1 / 100000))}
                    onChange={(event) =>
                      update(
                        "inlet_pressure_pa",
                        unscale(parseOptionalNumber(event.target.value), 1 / 100000),
                      )
                    }
                  />
                </label>
                <label>
                  ou niveau du bac amont (m)
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={numberInput(payload.inlet_tank_level_m)}
                    onChange={(event) =>
                      update("inlet_tank_level_m", parseOptionalNumber(event.target.value))
                    }
                    disabled={!tanks.length}
                  />
                  <small>
                    {tanks.length
                      ? "Converti en pression statique par le moteur."
                      : "Aucun bac dans cette version de modèle."}
                  </small>
                </label>
              </fieldset>

              <fieldset className="field-group">
                <legend>Condition aval</legend>
                <label>
                  Pression de sortie (bar abs.)
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={numberInput(scale(payload.outlet_pressure_pa, 1 / 100000))}
                    onChange={(event) =>
                      update(
                        "outlet_pressure_pa",
                        unscale(parseOptionalNumber(event.target.value), 1 / 100000),
                      )
                    }
                  />
                </label>
                <label>
                  ou niveau du bac aval (m)
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={numberInput(payload.outlet_tank_level_m)}
                    onChange={(event) =>
                      update("outlet_tank_level_m", parseOptionalNumber(event.target.value))
                    }
                    disabled={!tanks.length}
                  />
                </label>
              </fieldset>
            </div>

            <div
              className={boundary.valid ? "notice" : "notice notice-error"}
              role={boundary.valid ? undefined : "alert"}
            >
              {boundary.message}
            </div>
          </Panel>

          <Panel
            title="Pompes"
            description="État imposé et rapport de vitesse, par équipement du modèle."
          >
            {pumps.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Pompe</th>
                      <th>Rôle</th>
                      <th>État imposé</th>
                      <th>En marche</th>
                      <th>Rapport de vitesse</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pumps.map((pump) => {
                      const override = payload.pump_overrides.find(
                        (item) => item.pump_id === pump.code,
                      );
                      return (
                        <tr key={pump.id}>
                          <td>
                            <strong>{pump.code}</strong>
                            <small>{pump.name}</small>
                          </td>
                          <td>{pump.role === "standby" ? "Secours" : "Principale"}</td>
                          <td>
                            <select
                              value={override?.status ?? ""}
                              onChange={(event) =>
                                setPayload((current) => ({
                                  ...current,
                                  pump_overrides: upsertPumpOverride(
                                    current.pump_overrides,
                                    pump.code,
                                    { status: (event.target.value || null) as never },
                                  ),
                                }))
                              }
                            >
                              {EQUIPMENT_STATUSES.map((status) => (
                                <option key={status.value} value={status.value}>
                                  {status.label}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <select
                              value={booleanInput(override?.running ?? null)}
                              onChange={(event) =>
                                setPayload((current) => ({
                                  ...current,
                                  pump_overrides: upsertPumpOverride(
                                    current.pump_overrides,
                                    pump.code,
                                    { running: parseOptionalBoolean(event.target.value) },
                                  ),
                                }))
                              }
                            >
                              <option value="">Inchangé</option>
                              <option value="true">Oui</option>
                              <option value="false">Non</option>
                            </select>
                          </td>
                          <td>
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              value={numberInput(override?.speed_ratio ?? null)}
                              placeholder="1,00"
                              onChange={(event) =>
                                setPayload((current) => ({
                                  ...current,
                                  pump_overrides: upsertPumpOverride(
                                    current.pump_overrides,
                                    pump.code,
                                    { speed_ratio: parseOptionalNumber(event.target.value) },
                                  ),
                                }))
                              }
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="Aucune pompe placée"
                detail="Ajoutez des équipements dans la modélisation pour les piloter ici."
              />
            )}
          </Panel>

          <div className="content-grid equal">
            <Panel title="Stations" description="Stations disponibles ou contournées.">
              {stations.length ? (
                <ul className="issue-list">
                  {stations.map((station) => {
                    const override = payload.station_overrides.find(
                      (item) => item.station_id === station.code,
                    );
                    return (
                      <li key={station.id}>
                        <strong>{station.code}</strong>
                        <select
                          value={override?.status ?? ""}
                          onChange={(event) =>
                            setPayload((current) => ({
                              ...current,
                              station_overrides: upsertStationOverride(
                                current.station_overrides,
                                station.code,
                                (event.target.value || null) as never,
                              ),
                            }))
                          }
                        >
                          {EQUIPMENT_STATUSES.map((status) => (
                            <option key={status.value} value={status.value}>
                              {status.label}
                            </option>
                          ))}
                        </select>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <EmptyState
                  title="Aucune station"
                  detail="Cette version de modèle ne comporte pas de nœud de type station."
                />
              )}
            </Panel>

            <Panel title="Tronçons" description="Indisponibilités et pertes singulières ajoutées.">
              {edges.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Tronçon</th>
                        <th>État imposé</th>
                        <th>K additionnel</th>
                      </tr>
                    </thead>
                    <tbody>
                      {edges.map((edge) => {
                        const override = payload.segment_overrides.find(
                          (item) => item.segment_id === edge.code,
                        );
                        return (
                          <tr key={edge.id}>
                            <td>
                              <strong>{edge.code}</strong>
                            </td>
                            <td>
                              <select
                                value={override?.status ?? ""}
                                onChange={(event) =>
                                  setPayload((current) => ({
                                    ...current,
                                    segment_overrides: upsertSegmentOverride(
                                      current.segment_overrides,
                                      edge.code,
                                      { status: (event.target.value || null) as never },
                                    ),
                                  }))
                                }
                              >
                                {EQUIPMENT_STATUSES.map((status) => (
                                  <option key={status.value} value={status.value}>
                                    {status.label}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td>
                              <input
                                type="number"
                                step="0.1"
                                min="0"
                                value={numberInput(override?.additional_k ?? null)}
                                onChange={(event) =>
                                  setPayload((current) => ({
                                    ...current,
                                    segment_overrides: upsertSegmentOverride(
                                      current.segment_overrides,
                                      edge.code,
                                      { additional_k: parseOptionalNumber(event.target.value) },
                                    ),
                                  }))
                                }
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState
                  title="Aucun tronçon"
                  detail="Construisez le réseau avant de définir des indisponibilités."
                />
              )}
            </Panel>
          </div>

          <Panel
            title="Limites d'exploitation et options du solveur"
            description="Ces réglages entrent dans l'empreinte du calcul."
          >
            <div className="form-grid three">
              <label>
                Modèle de frottement
                <select
                  value={payload.solver.friction_model}
                  onChange={(event) =>
                    updateSolver("friction_model", event.target.value as never)
                  }
                >
                  {FRICTION_MODELS.map((model) => (
                    <option key={model.value} value={model.value}>
                      {model.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Vitesse minimale (m/s)
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={numberInput(payload.solver.min_velocity_m_s)}
                  onChange={(event) =>
                    updateSolver("min_velocity_m_s", parseOptionalNumber(event.target.value))
                  }
                />
              </label>
              <label>
                Vitesse maximale (m/s)
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={numberInput(payload.solver.max_velocity_m_s)}
                  onChange={(event) =>
                    updateSolver("max_velocity_m_s", parseOptionalNumber(event.target.value))
                  }
                />
              </label>
              <label>
                Débit maximal admissible (m³/h)
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={numberInput(scale(payload.solver.max_flow_m3_s, 3600))}
                  onChange={(event) =>
                    updateSolver(
                      "max_flow_m3_s",
                      unscale(parseOptionalNumber(event.target.value), 3600),
                    )
                  }
                />
                <small>Borne haute de la recherche lorsque le débit est inconnu.</small>
              </label>
              <label>
                Tolérance de pression (Pa)
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={String(payload.solver.pressure_tolerance_pa)}
                  onChange={(event) =>
                    updateSolver(
                      "pressure_tolerance_pa",
                      parseOptionalNumber(event.target.value) ?? 1,
                    )
                  }
                />
              </label>
              <label>
                Tolérance de bilan matière
                <input
                  type="number"
                  step="0.000001"
                  min="0"
                  value={String(payload.solver.mass_balance_tolerance)}
                  onChange={(event) =>
                    updateSolver(
                      "mass_balance_tolerance",
                      parseOptionalNumber(event.target.value) ?? 1e-6,
                    )
                  }
                />
              </label>
              <label>
                Itérations maximales
                <input
                  type="number"
                  step="1"
                  min="1"
                  value={String(payload.solver.max_iterations)}
                  onChange={(event) =>
                    updateSolver("max_iterations", parseOptionalNumber(event.target.value) ?? 100)
                  }
                />
              </label>
              <label>
                Pas d'échantillonnage du profil (m)
                <input
                  type="number"
                  step="1"
                  min="1"
                  value={String(payload.solver.profile_step_m)}
                  onChange={(event) =>
                    updateSolver("profile_step_m", parseOptionalNumber(event.target.value) ?? 1000)
                  }
                />
              </label>
              <label>
                Prix de l'énergie (€/J)
                <input
                  type="number"
                  step="0.00000001"
                  min="0"
                  value={numberInput(payload.energy_price_per_joule)}
                  onChange={(event) =>
                    update("energy_price_per_joule", parseOptionalNumber(event.target.value))
                  }
                />
              </label>
            </div>

            <div className="form-grid two">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={payload.solver.detect_gravity_zones}
                  onChange={(event) => updateSolver("detect_gravity_zones", event.target.checked)}
                />
                Détecter les zones gravitaires
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={payload.solver.apply_gravity_model}
                  onChange={(event) => updateSolver("apply_gravity_model", event.target.checked)}
                />
                Appliquer le modèle d'écoulement gravitaire
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={payload.solver.use_quadratic_pump_fit}
                  onChange={(event) => updateSolver("use_quadratic_pump_fit", event.target.checked)}
                />
                Ajuster les courbes de pompe par une quadratique
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={payload.solver.store_iterations}
                  onChange={(event) => updateSolver("store_iterations", event.target.checked)}
                />
                Conserver le détail des itérations
              </label>
            </div>
          </Panel>

          <Panel
            title="Vérification avant enregistrement"
            description="Contenu exact transmis au moteur."
          >
            <div className="button-row">
              <button
                className="button button-primary"
                disabled={!boundary.valid || createMutation.isPending || !name.trim()}
              >
                {createMutation.isPending ? "Enregistrement…" : "Enregistrer le scénario"}
              </button>
              <button
                type="button"
                className="button button-ghost"
                onClick={() => setShowCanonical((current) => !current)}
              >
                {showCanonical ? "Masquer l'entrée canonique" : "Afficher l'entrée canonique"}
              </button>
              <button
                type="button"
                className="button button-ghost"
                onClick={() => setPayload(DEFAULT_PAYLOAD)}
              >
                Réinitialiser
              </button>
            </div>
            {showCanonical ? (
              <pre className="code-editor" aria-label="Entrée canonique du scénario">
                {JSON.stringify(payload, null, 2)}
              </pre>
            ) : null}
          </Panel>
        </form>
      )}

      <Panel
        title="Scénarios de la version"
        description="Chaque scénario est calculable depuis « Calcul hydraulique »."
      >
        {scenarios.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Conditions</th>
                  <th>Créé le</th>
                </tr>
              </thead>
              <tbody>
                {scenarios.map((scenario) => (
                  <tr key={scenario.id}>
                    <td>
                      <strong>{scenario.name}</strong>
                      <small>{scenario.description ?? "Sans description"}</small>
                    </td>
                    <td>{summarizeConditions(scenario.payload)}</td>
                    <td>{scenario.created_at.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Aucun scénario"
            detail="Renseignez les conditions ci-dessus pour créer le premier scénario."
          />
        )}
      </Panel>
    </div>
  );
}

/**
 * Reproduit la règle de contrainte du moteur : le problème doit fournir soit un
 * débit imposé et une condition d'extrémité, soit les deux conditions d'extrémité.
 */
export function describeBoundaryConditions(
  payload: ScenarioPayload,
  hasTanks: boolean,
): { valid: boolean; message: string } {
  const inletKnown =
    payload.inlet_pressure_pa !== null || (hasTanks && payload.inlet_tank_level_m !== null);
  const outletKnown =
    payload.outlet_pressure_pa !== null || (hasTanks && payload.outlet_tank_level_m !== null);
  const flowKnown = payload.imposed_flow_m3_s !== null;

  if (flowKnown && inletKnown && outletKnown) {
    return {
      valid: false,
      message:
        "Problème sur-contraint : un débit imposé et deux conditions d'extrémité ne peuvent pas " +
        "être satisfaits simultanément. Retirez une des trois consignes.",
    };
  }
  if (flowKnown && (inletKnown || outletKnown)) {
    return {
      valid: true,
      message:
        "Problème correctement contraint : débit imposé et " +
        (inletKnown ? "condition amont" : "condition aval") +
        ". Le moteur résout le profil de pression.",
    };
  }
  if (!flowKnown && inletKnown && outletKnown) {
    return {
      valid: true,
      message:
        "Problème correctement contraint : conditions amont et aval imposées. Le moteur " +
        "recherche le débit compatible.",
    };
  }
  return {
    valid: false,
    message:
      "Problème sous-contraint : le moteur exige exactement deux conditions indépendantes " +
      "parmi le débit imposé, la condition amont et la condition aval.",
  };
}

function summarizeConditions(payload: Record<string, unknown>): string {
  const parts: string[] = [];
  const flow = payload.imposed_flow_m3_s;
  if (typeof flow === "number") {
    parts.push((flow * 3600).toFixed(1) + " m³/h imposés");
  }
  const inlet = payload.inlet_pressure_pa;
  if (typeof inlet === "number") {
    parts.push("amont " + (inlet / 100000).toFixed(2) + " bar");
  }
  const outlet = payload.outlet_pressure_pa;
  if (typeof outlet === "number") {
    parts.push("aval " + (outlet / 100000).toFixed(2) + " bar");
  }
  const inletLevel = payload.inlet_tank_level_m;
  if (typeof inletLevel === "number") {
    parts.push("bac amont " + inletLevel.toFixed(2) + " m");
  }
  const outletLevel = payload.outlet_tank_level_m;
  if (typeof outletLevel === "number") {
    parts.push("bac aval " + outletLevel.toFixed(2) + " m");
  }
  return parts.length ? parts.join(", ") : "Conditions non renseignées";
}

function upsertPumpOverride(
  overrides: PumpOverride[],
  pumpId: string,
  patch: Partial<Omit<PumpOverride, "pump_id">>,
): PumpOverride[] {
  const existing = overrides.find((item) => item.pump_id === pumpId);
  const merged: PumpOverride = {
    pump_id: pumpId,
    status: existing?.status ?? null,
    running: existing?.running ?? null,
    speed_ratio: existing?.speed_ratio ?? null,
    ...patch,
  };
  const others = overrides.filter((item) => item.pump_id !== pumpId);
  if (merged.status === null && merged.running === null && merged.speed_ratio === null) {
    return others;
  }
  return [...others, merged];
}

function upsertStationOverride(
  overrides: StationOverride[],
  stationId: string,
  status: StationOverride["status"],
): StationOverride[] {
  const others = overrides.filter((item) => item.station_id !== stationId);
  return status === null ? others : [...others, { station_id: stationId, status }];
}

function upsertSegmentOverride(
  overrides: SegmentOverride[],
  segmentId: string,
  patch: Partial<Omit<SegmentOverride, "segment_id">>,
): SegmentOverride[] {
  const existing = overrides.find((item) => item.segment_id === segmentId);
  const merged: SegmentOverride = {
    segment_id: segmentId,
    status: existing?.status ?? null,
    additional_k: existing?.additional_k ?? null,
    ...patch,
  };
  const others = overrides.filter((item) => item.segment_id !== segmentId);
  if (merged.status === null && merged.additional_k === null) {
    return others;
  }
  return [...others, merged];
}

function parseOptionalNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseOptionalBoolean(value: string): boolean | null {
  if (value === "true") {
    return true;
  }
  if (value === "false") {
    return false;
  }
  return null;
}

function booleanInput(value: boolean | null): string {
  return value === null ? "" : String(value);
}

function numberInput(value: number | null): string {
  return value === null ? "" : String(value);
}

function scale(value: number | null, factor: number): number | null {
  return value === null ? null : value * factor;
}

function unscale(value: number | null, factor: number): number | null {
  return value === null ? null : value / factor;
}

function kelvinToCelsiusInput(value: number | null): string {
  return value === null ? "" : String(Number((value - 273.15).toFixed(4)));
}

function celsiusInputToKelvin(value: string): number | null {
  const parsed = parseOptionalNumber(value);
  return parsed === null ? null : parsed + 273.15;
}
