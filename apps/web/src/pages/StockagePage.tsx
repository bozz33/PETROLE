import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest, jsonBody } from "../api";
import {
  EmptyState,
  ErrorNotice,
  Panel,
  StatusBadge,
  SuccessNotice,
} from "../components/Shell";
import type { Organization, Page, Tank, Transfer } from "../types";
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
  const [sourceId, setSourceId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [balance, setBalance] = useState<BalanceResult | null>(null);

  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<Page<Organization>>("/organizations?limit=200&offset=0"),
  });
  const tanksQuery = useQuery({
    queryKey: ["tanks", organizationId],
    queryFn: () =>
      apiRequest<Page<Tank>>(
        "/tanks?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });

  const organizations = organizationsQuery.data?.items ?? [];
  const tanks = tanksQuery.data?.items ?? [];

  useEffect(() => {
    if (!organizationId && organizations.length) {
      setOrganizationId(organizations[0].id);
    }
  }, [organizationId, organizations]);

  useEffect(() => {
    if (!tanks.some((tank) => tank.id === sourceId)) {
      setSourceId(tanks[0]?.id ?? "");
    }
    if (!tanks.some((tank) => tank.id === destinationId) || destinationId === sourceId) {
      setDestinationId(tanks.find((tank) => tank.id !== (tanks[0]?.id ?? ""))?.id ?? "");
    }
  }, [destinationId, sourceId, tanks]);

  const tankMutation = useMutation({
    mutationFn: (form: FormData) => {
      const height = Number(form.get("height_m"));
      const capacity = Number(form.get("capacity_m3"));
      const currentLevel = Number(form.get("current_level_m"));
      return apiRequest<Tank>("/tanks", {
        method: "POST",
        body: jsonBody({
          organization_id: organizationId,
          name: form.get("name"),
          code: form.get("code"),
          tank_type: "vertical_fixed_roof",
          elevation_m: Number(form.get("elevation_m")),
          current_level_m: currentLevel,
          fluid_id: String(form.get("fluid_id") || "").trim() || null,
          compatible_fluid_ids: String(form.get("compatible_fluid_ids") || "")
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean),
          levels: {
            minimum_m: height * 0.05,
            low_m: height * 0.1,
            normal_m: height * 0.5,
            high_m: height * 0.9,
            high_high_m: height * 0.95,
          },
          strapping: [
            { height_m: 0, volume_m3: 0 },
            { height_m: height, volume_m3: capacity },
          ],
        }),
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tanks", organizationId] });
    },
  });

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
            target_volume_m3: Number(form.get("target_volume_m3")),
            time_step_s: Number(form.get("time_step_s")),
            loss_fraction: Number(form.get("loss_percent")) / 100,
            absorbed_power_w:
              Number(form.get("power_kw")) > 0
                ? Number(form.get("power_kw")) * 1_000
                : null,
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
  const error =
    organizationsQuery.error ??
    tanksQuery.error ??
    tankMutation.error ??
    transferMutation.error ??
    balanceMutation.error;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {tankMutation.isSuccess ? (
        <SuccessNotice>Le bac d'étude et son barémage théorique ont été enregistrés.</SuccessNotice>
      ) : null}

      <Panel
        title="Parc de stockage"
        description="Volumes et marges calculés exclusivement depuis le barémage du bac."
      >
        <label>
          Organisation
          <select
            value={organizationId}
            onChange={(event) => setOrganizationId(event.target.value)}
          >
            <option value="">Sélectionner</option>
            {organizations.map((organization) => (
              <option key={organization.id} value={organization.id}>
                {organization.name}
              </option>
            ))}
          </select>
        </label>
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
          <summary>Créer un bac d'étude avec barémage théorique</summary>
          <form
            className="compact-form"
            onSubmit={(event) => {
              event.preventDefault();
              tankMutation.mutate(new FormData(event.currentTarget));
            }}
          >
            <div className="form-grid three">
              <label>Nom<input name="name" required /></label>
              <label>Code<input name="code" required /></label>
              <label>Produit courant<input name="fluid_id" placeholder="diesel" /></label>
              <label>Hauteur barémée (m)<input name="height_m" type="number" min="0.1" step="any" defaultValue="12" required /></label>
              <label>Capacité (m³)<input name="capacity_m3" type="number" min="1" step="any" defaultValue="10000" required /></label>
              <label>Niveau courant (m)<input name="current_level_m" type="number" min="0" step="any" defaultValue="6" required /></label>
              <label>Altitude du fond (m)<input name="elevation_m" type="number" step="any" defaultValue="0" /></label>
              <label>Produits compatibles<input name="compatible_fluid_ids" placeholder="diesel, kerosene" /></label>
            </div>
            <p className="field-help">
              Ce barémage linéaire est réservé aux études et tests. Importez une table de jaugeage
              certifiée avant toute utilisation opérationnelle.
            </p>
            <button className="button button-primary" disabled={!organizationId || tankMutation.isPending}>
              Créer le bac d'étude
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
              <label>Débit (m³/h)<input name="flow_m3_h" type="number" min="0.001" step="any" defaultValue="360" required /></label>
              <label>Volume cible (m³)<input name="target_volume_m3" type="number" min="0.001" step="any" defaultValue="100" required /></label>
              <label>Pas de calcul (s)<input name="time_step_s" type="number" min="0.1" step="any" defaultValue="60" required /></label>
              <label>Pertes (%)<input name="loss_percent" type="number" min="0" max="99" step="any" defaultValue="0" /></label>
              <label>Puissance absorbée (kW)<input name="power_kw" type="number" min="0" step="any" defaultValue="0" /></label>
            </div>
            <button
              className="button button-primary"
              disabled={!sourceId || !destinationId || transferMutation.isPending}
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
