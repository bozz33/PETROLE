import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { OrganizationField } from "../components/OrganizationField";
import { apiRequest, jsonBody } from "../api";
import {
  EmptyState,
  ErrorNotice,
  Panel,
  StatusBadge,
  SuccessNotice,
} from "../components/Shell";
import { defaultTankDraft, TankForm, validateTank } from "../components/tanks/TankForm";
import type {
  ModelVersion,
  Page,
  Project,
  Scenario,
  Tank,
  TankDraft,
  Transfer,
} from "../types";
import { formatNumber } from "../types";

interface BalanceResult {
  system_imbalance_m3: number;
  expanded_uncertainty_m3: number;
  acceptance_limit_m3: number;
  within_tolerance: boolean;
}

export function StockagePage() {
  const queryClient = useQueryClient();
  const [organizationId, setOrganizationId] = useState("");
  const [tankDraft, setTankDraft] = useState<TankDraft>(defaultTankDraft);
  const [sourceId, setSourceId] = useState("");
  const [objective, setObjective] = useState<TransferObjective>("volume");
  const [transferProjectId, setTransferProjectId] = useState("");
  const [transferModelId, setTransferModelId] = useState("");
  const [transferScenarioId, setTransferScenarioId] = useState("");
  const [hydraulicCoupling, setHydraulicCoupling] = useState(false);
  const [destinationId, setDestinationId] = useState("");
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [balance, setBalance] = useState<BalanceResult | null>(null);

  const tanksQuery = useQuery({
    queryKey: ["tanks", organizationId],
    queryFn: () =>
      apiRequest<Page<Tank>>(
        "/tanks?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });

  const tanks = tanksQuery.data?.items ?? [];


  useEffect(() => {
    if (!tanks.some((tank) => tank.id === sourceId)) {
      setSourceId(tanks[0]?.id ?? "");
    }
    if (!tanks.some((tank) => tank.id === destinationId) || destinationId === sourceId) {
      setDestinationId(tanks.find((tank) => tank.id !== (tanks[0]?.id ?? ""))?.id ?? "");
    }
  }, [destinationId, sourceId, tanks]);

  const tankMutation = useMutation({
    mutationFn: () => {
      const { strapping_origin: _origin, ...payload } = tankDraft;
      return apiRequest<Tank>("/tanks", {
        method: "POST",
        body: jsonBody({ organization_id: organizationId, ...payload }),
      });
    },
    onSuccess: async () => {
      setTankDraft(defaultTankDraft());
      await queryClient.invalidateQueries({ queryKey: ["tanks", organizationId] });
    },
  });

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiRequest<Page<Project>>("/projects?limit=200&offset=0"),
    enabled: hydraulicCoupling,
  });
  const modelsQuery = useQuery({
    queryKey: ["models", transferProjectId],
    queryFn: () =>
      apiRequest<Page<ModelVersion>>(
        "/projects/" + transferProjectId + "/models?limit=200&offset=0",
      ),
    enabled: hydraulicCoupling && Boolean(transferProjectId),
  });
  const scenariosQuery = useQuery({
    queryKey: ["scenarios", transferModelId],
    queryFn: () =>
      apiRequest<Page<Scenario>>("/models/" + transferModelId + "/scenarios?limit=200&offset=0"),
    enabled: hydraulicCoupling && Boolean(transferModelId),
  });

  const transferProjects = projectsQuery.data?.items ?? [];
  const transferModels = modelsQuery.data?.items ?? [];
  const transferScenarios = scenariosQuery.data?.items ?? [];

  useEffect(() => {
    if (!hydraulicCoupling) {
      return;
    }
    if (!transferProjects.some((project) => project.id === transferProjectId)) {
      setTransferProjectId(transferProjects[0]?.id ?? "");
    }
  }, [hydraulicCoupling, transferProjectId, transferProjects]);

  useEffect(() => {
    if (!transferModels.some((model) => model.id === transferModelId)) {
      setTransferModelId(transferModels[0]?.id ?? "");
    }
  }, [transferModelId, transferModels]);

  useEffect(() => {
    if (!transferScenarios.some((item) => item.id === transferScenarioId)) {
      setTransferScenarioId(transferScenarios[0]?.id ?? "");
    }
  }, [transferScenarioId, transferScenarios]);

  const transferMutation = useMutation({
    mutationFn: (form: FormData) => {
      return apiRequest<Transfer>(
        "/organizations/" + organizationId + "/transfers",
        {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID() },
          body: jsonBody({
            source_tank_id: sourceId,
            destination_tank_id: destinationId,
            fluid_id: form.get("fluid_id"),
            requested_flow_m3_s: Number(form.get("flow_m3_h")) / 3_600,
            // Le moteur exige exactement un objectif : les deux autres restent nuls.
            target_volume_m3:
              objective === "volume" ? numberField(form, "target_volume_m3") : null,
            target_destination_level_m:
              objective === "level" ? numberField(form, "target_level_m") : null,
            target_duration_s:
              objective === "duration"
                ? multiplyOrNull(numberField(form, "target_duration_h"), 3_600)
                : null,
            time_step_s: Number(form.get("time_step_s")),
            maximum_flow_m3_s: divideOrNull(numberField(form, "maximum_flow_m3_h"), 3_600),
            maximum_duration_s: multiplyOrNull(
              numberField(form, "maximum_duration_h"),
              3_600,
            ) ?? 31_536_000,
            loss_fraction: Number(form.get("loss_percent")) / 100,
            discharge_pressure_pa: multiplyOrNull(
              numberField(form, "discharge_pressure_bar"),
              100_000,
            ),
            absorbed_power_w: multiplyOrNull(numberField(form, "power_kw"), 1_000),
            scenario_id: hydraulicCoupling ? transferScenarioId || null : null,
          }),
        },
      );
    },
    onSuccess: (value) => {
      setTransfer(value);
      setBalance(null);
    },
  });

  const balanceMutation = useMutation({
    mutationFn: () => {
      if (!transfer) {
        throw new Error("Aucun transfert n'est disponible.");
      }
      const source = tanks.find((tank) => tank.id === transfer.source_tank_id);
      const destination = tanks.find(
        (tank) => tank.id === transfer.destination_tank_id,
      );
      if (!source || !destination) {
        throw new Error("Les réservoirs du transfert sont introuvables.");
      }
      const result = transfer.result_payload;
      return apiRequest<BalanceResult>("/transfers/" + transfer.id + "/balance", {
        method: "POST",
        body: jsonBody({
          source_opening: {
            value_m3: source.current_volume_m3,
            standard_uncertainty_m3: 0.5,
          },
          source_closing: {
            value_m3: source.current_volume_m3 - result.withdrawn_volume_m3,
            standard_uncertainty_m3: 0.5,
          },
          destination_opening: {
            value_m3: destination.current_volume_m3,
            standard_uncertainty_m3: 0.5,
          },
          destination_closing: {
            value_m3: destination.current_volume_m3 + result.received_volume_m3,
            standard_uncertainty_m3: 0.5,
          },
          metered_volume: {
            value_m3: result.withdrawn_volume_m3,
            standard_uncertainty_m3: 0.25,
          },
          accounted_losses: {
            value_m3: result.losses_m3,
            standard_uncertainty_m3: 0.1,
          },
          relative_tolerance: 0.001,
        }),
      });
    },
    onSuccess: setBalance,
  });

  const selectedSource = useMemo(
    () => tanks.find((tank) => tank.id === sourceId),
    [sourceId, tanks],
  );
  // Les écarts ne sont signalés qu'une fois la fiche entamée : afficher une
  // alerte sur un formulaire encore vierge n'apporte rien à l'utilisateur.
  const tankTouched = Boolean(tankDraft.name.trim() || tankDraft.code.trim());
  const tankProblems = validateTank(tankDraft);
  const visibleTankProblems = tankTouched ? tankProblems : [];
  const error =
    tanksQuery.error ??
    tankMutation.error ??
    transferMutation.error ??
    balanceMutation.error;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {tankMutation.isSuccess ? (
        <SuccessNotice>Le bac et sa table de barémage ont été enregistrés.</SuccessNotice>
      ) : null}

      <Panel
        title="Parc de stockage"
        description="Volumes et marges calculés exclusivement depuis le barémage du bac."
      >
          <OrganizationField value={organizationId} onChange={setOrganizationId} />
        {tanks.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Bac</th>
                  <th>Produit</th>
                  <th>Niveau</th>
                  <th>Stock</th>
                  <th>Capacité disponible</th>
                  <th>État</th>
                </tr>
              </thead>
              <tbody>
                {tanks.map((tank) => (
                  <tr key={tank.id}>
                    <td>
                      <strong>{tank.code}</strong>
                      <small>{tank.name}</small>
                    </td>
                    <td>{tank.fluid_id ?? "Disponible"}</td>
                    <td>{formatNumber(tank.current_level_m)} m</td>
                    <td>{formatNumber(tank.current_volume_m3)} m³</td>
                    <td>{formatNumber(tank.available_capacity_m3)} m³</td>
                    <td><StatusBadge value={tank.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Aucun réservoir"
            detail="Créez un premier bac ou importez son barémage dans la section Données."
          />
        )}

        <details className="editor-details" open={!tanks.length && Boolean(organizationId)}>
          <summary>Créer un bac</summary>
          <form
            className="compact-form"
            onSubmit={(event) => {
              event.preventDefault();
              tankMutation.mutate();
            }}
          >
            <TankForm value={tankDraft} onChange={setTankDraft} />
            {visibleTankProblems.length ? (
              <div className="notice notice-error" role="alert">
                <ul className="issue-list negative">
                  {visibleTankProblems.map((problem) => (
                    <li key={problem}>
                      <span>{problem}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <button
              className="button button-primary"
              disabled={!organizationId || tankMutation.isPending || tankProblems.length > 0}
            >
              {tankDraft.strapping_origin === "theoretical"
                ? "Créer le bac d'étude avec barémage théorique"
                : "Créer le bac avec sa table de jaugeage"}
            </button>
          </form>
        </details>
      </Panel>

      <Panel
        title="Simulation bac-à-bac"
        description="Le calcul s'arrête exactement à l'objectif ou au premier seuil de sécurité."
      >
        {tanks.length >= 2 ? (
          <form
            className="compact-form"
            onSubmit={(event) => {
              event.preventDefault();
              transferMutation.mutate(new FormData(event.currentTarget));
            }}
          >
            <div className="form-grid three">
              <label>
                Bac source
                <select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
                  {tanks.map((tank) => <option key={tank.id} value={tank.id}>{tank.code}</option>)}
                </select>
              </label>
              <label>
                Bac destination
                <select value={destinationId} onChange={(event) => setDestinationId(event.target.value)}>
                  {tanks.filter((tank) => tank.id !== sourceId).map((tank) => (
                    <option key={tank.id} value={tank.id}>{tank.code}</option>
                  ))}
                </select>
              </label>
              <label>Produit<input name="fluid_id" defaultValue={selectedSource?.fluid_id ?? ""} required /></label>
              <label>Débit demandé (m³/h)<input name="flow_m3_h" type="number" min="0.001" step="any" defaultValue="360" required /></label>
              <label>Pas de calcul (s)<input name="time_step_s" type="number" min="0.1" step="any" defaultValue="60" required /></label>
            </div>

            <fieldset className="field-group">
              <legend>Objectif du mouvement</legend>
              <div className="form-grid three">
                <label>
                  Critère d'arrêt
                  <select
                    value={objective}
                    onChange={(event) => setObjective(event.target.value as TransferObjective)}
                  >
                    <option value="volume">Volume transféré</option>
                    <option value="level">Niveau du bac destination</option>
                    <option value="duration">Durée</option>
                  </select>
                </label>
                {objective === "volume" ? (
                  <label>Volume cible (m³)<input name="target_volume_m3" type="number" min="0.001" step="any" defaultValue="100" required /></label>
                ) : null}
                {objective === "level" ? (
                  <label>Niveau destination visé (m)<input name="target_level_m" type="number" min="0.001" step="any" defaultValue="5" required /></label>
                ) : null}
                {objective === "duration" ? (
                  <label>Durée visée (h)<input name="target_duration_h" type="number" min="0.001" step="any" defaultValue="2" required /></label>
                ) : null}
              </div>
              <p className="field-help">
                Le calcul s'arrête à l'objectif ou au premier seuil de sécurité atteint,
                selon ce qui survient en premier.
              </p>
            </fieldset>

            <fieldset className="field-group">
              <legend>Limites d'exploitation</legend>
              <div className="form-grid three">
                <label>Débit maximal (m³/h)<input name="maximum_flow_m3_h" type="number" min="0" step="any" placeholder="Sans limite" /></label>
                <label>Durée maximale (h)<input name="maximum_duration_h" type="number" min="0" step="any" placeholder="Sans limite" /></label>
                <label>Pertes (%)<input name="loss_percent" type="number" min="0" max="99" step="any" defaultValue="0" /></label>
                <label>Pression de refoulement (bar abs.)<input name="discharge_pressure_bar" type="number" min="0" step="any" placeholder="Déduite du réseau si couplé" /></label>
                <label>Puissance absorbée (kW)<input name="power_kw" type="number" min="0" step="any" placeholder="Déduite du réseau si couplé" /></label>
              </div>
            </fieldset>

            <fieldset className="field-group">
              <legend>Chemin hydraulique</legend>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={hydraulicCoupling}
                  onChange={(event) => setHydraulicCoupling(event.target.checked)}
                />
                Déterminer le débit par le réseau plutôt que l'imposer
              </label>
              {hydraulicCoupling ? (
                <div className="form-grid three">
                  <label>
                    Projet
                    <select value={transferProjectId} onChange={(event) => setTransferProjectId(event.target.value)}>
                      <option value="">Sélectionner</option>
                      {transferProjects.map((project) => (
                        <option key={project.id} value={project.id}>{project.code} — {project.name}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Version de modèle
                    <select value={transferModelId} onChange={(event) => setTransferModelId(event.target.value)} disabled={!transferProjectId}>
                      <option value="">Sélectionner</option>
                      {transferModels.map((model) => (
                        <option key={model.id} value={model.id}>V{model.version_number} — {model.name}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Scénario du transfert
                    <select value={transferScenarioId} onChange={(event) => setTransferScenarioId(event.target.value)} disabled={!transferModelId}>
                      <option value="">Sélectionner</option>
                      {transferScenarios.map((item) => (
                        <option key={item.id} value={item.id}>{item.name}</option>
                      ))}
                    </select>
                  </label>
                </div>
              ) : (
                <p className="field-help">
                  Sans chemin hydraulique, le débit demandé est imposé : la simulation
                  intègre des volumes et des niveaux, sans vérifier la faisabilité du réseau.
                </p>
              )}
            </fieldset>
            <button
              className="button button-primary"
              disabled={
                !sourceId ||
                !destinationId ||
                transferMutation.isPending ||
                (hydraulicCoupling && !transferScenarioId)
              }
            >
              {transferMutation.isPending ? "Simulation…" : "Simuler et archiver"}
            </button>
          </form>
        ) : (
          <EmptyState title="Deux bacs requis" detail="Ajoutez une source et une destination." />
        )}

        {transfer ? (
          <div className="report-result">
            <section className="metrics-grid">
              <TransferMetric label="Durée" value={formatNumber(transfer.result_payload.duration_s / 60)} unit="min" />
              <TransferMetric label="Soutiré" value={formatNumber(transfer.result_payload.withdrawn_volume_m3)} unit="m³" />
              <TransferMetric label="Reçu" value={formatNumber(transfer.result_payload.received_volume_m3)} unit="m³" />
              <TransferMetric label="Résidu" value={formatNumber(transfer.result_payload.balance_residual_m3, 8)} unit="m³" />
            </section>
            <div className="button-row">
              <StatusBadge value={transfer.status} />
              <button className="button button-secondary" onClick={() => balanceMutation.mutate()} disabled={balanceMutation.isPending}>
                Calculer le bilan matière
              </button>
            </div>
            {transfer.result_payload.hydraulic_coupling ? (
              <div className="resource-summary">
                <div>
                  <span>Débit</span>
                  <strong>Déterminé par le réseau</strong>
                </div>
                <div>
                  <span>Moteur</span>
                  <strong>{transfer.result_payload.hydraulic_coupling.engine_version}</strong>
                </div>
                <div>
                  <span>Calculs hydrauliques</span>
                  <strong>{transfer.result_payload.hydraulic_coupling.evaluations}</strong>
                </div>
                <div>
                  <span>Points réutilisés</span>
                  <strong>{transfer.result_payload.hydraulic_coupling.reused_points}</strong>
                </div>
                <div>
                  <span>Pompes en marche</span>
                  <strong>
                    {transfer.result_payload.hydraulic_coupling.pump_ids.join(", ") || "aucune"}
                  </strong>
                </div>
                {transfer.result_payload.hydraulic_coupling.failures.length ? (
                  <div>
                    <span>Points non résolus</span>
                    <strong>
                      {transfer.result_payload.hydraulic_coupling.failures.length}
                    </strong>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="field-help">
                Débit imposé par l'utilisateur : la faisabilité du réseau n'a pas été vérifiée.
              </p>
            )}
            {balance ? (
              <div className="notice">
                <StatusBadge value={balance.within_tolerance ? "conforme" : "hors_tolerance"} />
                Écart {formatNumber(balance.system_imbalance_m3, 6)} m³ · limite {formatNumber(balance.acceptance_limit_m3, 6)} m³
              </div>
            ) : null}
          </div>
        ) : null}
      </Panel>
    </div>
  );
}

function TransferMetric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <article className="metric-card green">
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{unit}</small>
    </article>
  );
}

/** Critère d'arrêt retenu ; le moteur en exige exactement un. */
type TransferObjective = "volume" | "level" | "duration";

function numberField(form: FormData, name: string): number | null {
  const raw = form.get(name);
  if (typeof raw !== "string" || !raw.trim()) {
    return null;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function multiplyOrNull(value: number | null, factor: number): number | null {
  return value === null ? null : value * factor;
}

function divideOrNull(value: number | null, factor: number): number | null {
  return value === null ? null : value / factor;
}
