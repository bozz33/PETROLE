/**
 * Restitution complète d'un calcul hydraulique.
 *
 * Le moteur produit un bilan par tronçon, par station et par pompe, ainsi que
 * les informations numériques de résolution. Ces sorties sont exigées par la
 * définition du MVP et étaient jusqu'ici absentes de l'interface.
 */

import { EmptyState, Panel, StatusBadge } from "../Shell";
import type {
  CalculationPayload,
  PumpResultRow,
  SegmentResultRow,
  StationResultRow,
} from "../../types";
import { formatNumber } from "../../types";

export function SegmentResultsPanel({ segments }: { segments: SegmentResultRow[] }) {
  if (!segments.length) {
    return (
      <Panel title="Résultats par tronçon" description="Vitesse, régime, frottement et pressions.">
        <EmptyState
          title="Aucun tronçon détaillé"
          detail="Le moteur n'a pas produit de bilan par tronçon pour ce calcul."
        />
      </Panel>
    );
  }

  return (
    <Panel
      title="Résultats par tronçon"
      description="Vitesse, nombre de Reynolds, frottement, pertes et pressions."
    >
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Tronçon</th>
              <th>Débit (m³/h)</th>
              <th>Vitesse (m/s)</th>
              <th>Reynolds</th>
              <th>Régime</th>
              <th>Frottement</th>
              <th>Pertes (m)</th>
              <th>Entrée (bar)</th>
              <th>Sortie (bar)</th>
              <th>Marge MAOP (bar)</th>
            </tr>
          </thead>
          <tbody>
            {segments.map((segment) => (
              <tr key={segment.segment_id}>
                <td>
                  <strong>{segment.segment_id}</strong>
                  <small>{segment.label ?? segment.friction_model}</small>
                </td>
                <td>{formatNumber(segment.flow_m3_s * 3600)}</td>
                <td>{formatNumber(segment.velocity_m_s)}</td>
                <td>{formatNumber(segment.reynolds, 0)}</td>
                <td>{segment.flow_regime}</td>
                <td>{formatNumber(segment.friction_factor, 5)}</td>
                <td>
                  {formatNumber(segment.total_head_loss_m)}
                  <small>
                    linéaire {formatNumber(segment.friction_head_loss_m)} · singulière{" "}
                    {formatNumber(segment.minor_head_loss_m)}
                  </small>
                </td>
                <td>{formatNumber(segment.inlet_pressure_pa / 100000)}</td>
                <td>{formatNumber(segment.outlet_pressure_pa / 100000)}</td>
                <td>
                  {segment.maop_margin_pa === null
                    ? "—"
                    : formatNumber(segment.maop_margin_pa / 100000)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

export function StationResultsPanel({ stations }: { stations: StationResultRow[] }) {
  if (!stations.length) {
    return (
      <Panel title="Résultats par station" description="Aspiration, refoulement et puissance.">
        <EmptyState
          title="Aucune station"
          detail="Le modèle calculé ne comporte pas de station de pompage."
        />
      </Panel>
    );
  }

  return (
    <>
      <Panel
        title="Résultats par station"
        description="Pressions d'aspiration et de refoulement, hauteur et puissance."
      >
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Station</th>
                <th>Chaînage (km)</th>
                <th>État</th>
                <th>Débit (m³/h)</th>
                <th>Aspiration (bar)</th>
                <th>Refoulement (bar)</th>
                <th>Différentiel (bar)</th>
                <th>Hauteur (m)</th>
                <th>Puissance absorbée (kW)</th>
                <th>Rendement</th>
                <th>Pompes actives</th>
              </tr>
            </thead>
            <tbody>
              {stations.map((station) => (
                <tr key={station.station_id}>
                  <td>
                    <strong>{station.station_id}</strong>
                    <small>{station.name}</small>
                  </td>
                  <td>{formatNumber(station.chainage_m / 1000, 3)}</td>
                  <td>
                    <StatusBadge
                      value={
                        station.bypassed
                          ? "contournée"
                          : station.in_service
                            ? "en service"
                            : "à l'arrêt"
                      }
                    />
                  </td>
                  <td>{formatNumber(station.flow_m3_s * 3600)}</td>
                  <td>{formatNumber(station.suction_pressure_pa / 100000)}</td>
                  <td>{formatNumber(station.discharge_pressure_pa / 100000)}</td>
                  <td>{formatNumber(station.differential_pressure_pa / 100000)}</td>
                  <td>{formatNumber(station.head_m)}</td>
                  <td>
                    {station.absorbed_power_w === null
                      ? "—"
                      : formatNumber(station.absorbed_power_w / 1000)}
                  </td>
                  <td>
                    {station.efficiency === null ? "—" : formatNumber(station.efficiency * 100, 1) + " %"}
                  </td>
                  <td>{station.active_pump_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <PumpResultsPanel pumps={stations.flatMap((station) => station.pumps)} />
    </>
  );
}

export function PumpResultsPanel({ pumps }: { pumps: PumpResultRow[] }) {
  if (!pumps.length) {
    return null;
  }

  return (
    <Panel
      title="Résultats par pompe"
      description="Hauteur, rendement, puissance et marge de NPSH."
    >
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Pompe</th>
              <th>Station</th>
              <th>Marche</th>
              <th>Débit (m³/h)</th>
              <th>Hauteur (m)</th>
              <th>Vitesse</th>
              <th>Rendement</th>
              <th>Hydraulique (kW)</th>
              <th>Absorbée (kW)</th>
              <th>NPSHa (m)</th>
              <th>NPSHr (m)</th>
              <th>Marge NPSH (m)</th>
              <th>Domaine</th>
            </tr>
          </thead>
          <tbody>
            {pumps.map((pump) => (
              <tr key={pump.pump_id}>
                <td>
                  <strong>{pump.pump_id}</strong>
                  <small>{pump.label}</small>
                </td>
                <td>{pump.station_id}</td>
                <td>
                  <StatusBadge value={pump.running ? "en marche" : "à l'arrêt"} />
                </td>
                <td>{formatNumber(pump.flow_m3_s * 3600)}</td>
                <td>{formatNumber(pump.head_m)}</td>
                <td>{formatNumber(pump.speed_ratio, 3)}</td>
                <td>
                  {pump.efficiency === null ? "—" : formatNumber(pump.efficiency * 100, 1) + " %"}
                </td>
                <td>
                  {pump.hydraulic_power_w === null
                    ? "—"
                    : formatNumber(pump.hydraulic_power_w / 1000)}
                </td>
                <td>
                  {pump.absorbed_power_w === null
                    ? "—"
                    : formatNumber(pump.absorbed_power_w / 1000)}
                </td>
                <td>{pump.npsh_available_m === null ? "—" : formatNumber(pump.npsh_available_m)}</td>
                <td>{pump.npsh_required_m === null ? "—" : formatNumber(pump.npsh_required_m)}</td>
                <td>
                  {pump.npsh_margin_m === null ? (
                    "—"
                  ) : (
                    <StatusBadge
                      value={
                        pump.npsh_margin_m >= 0
                          ? formatNumber(pump.npsh_margin_m) + " (suffisante)"
                          : formatNumber(pump.npsh_margin_m) + " (insuffisante)"
                      }
                    />
                  )}
                </td>
                <td>
                  <StatusBadge
                    value={pump.within_curve_domain ? "dans la courbe" : "hors courbe"}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

export function NumericalSummaryPanel({
  summary,
  engineVersion,
  inputHash,
}: {
  summary: CalculationPayload;
  engineVersion: string;
  inputHash: string;
}) {
  const diagnostics = summary.diagnostics ?? {};

  return (
    <Panel
      title="Informations numériques"
      description="Méthode, convergence et empreinte du calcul."
    >
      <div className="resource-summary">
        <div>
          <span>Méthode</span>
          <strong>{String(diagnostics.method ?? "non publiée")}</strong>
        </div>
        <div>
          <span>Convergence</span>
          <StatusBadge value={diagnostics.converged ? "convergé" : "non convergé"} />
        </div>
        <div>
          <span>Itérations</span>
          <strong>{diagnostics.iterations === undefined ? "—" : String(diagnostics.iterations)}</strong>
        </div>
        <div>
          <span>Résidu</span>
          <strong>
            {diagnostics.residual === undefined ? "—" : formatNumber(diagnostics.residual, 10)}
          </strong>
        </div>
        <div>
          <span>Durée de calcul</span>
          <strong>
            {diagnostics.duration_s === undefined
              ? "—"
              : formatNumber(diagnostics.duration_s, 4) + " s"}
          </strong>
        </div>
        <div>
          <span>Moteur</span>
          <strong>{engineVersion}</strong>
        </div>
        <div>
          <span>Empreinte d'entrée</span>
          <strong className="mono hash">{inputHash}</strong>
        </div>
      </div>
    </Panel>
  );
}
