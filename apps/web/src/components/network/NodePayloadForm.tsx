/**
 * Champs propres à chaque type de nœud du réseau.
 *
 * Le backend expose des schémas distincts par type (station, injection,
 * soutirage, terminal). L'interface les présente ici au lieu d'un objet libre,
 * afin que l'ingénieur n'ait jamais à écrire de JSON pour un cas courant.
 */

import type { NetworkNode, NodePayload, StationConfiguration } from "../../types";

const ARRANGEMENTS: Array<{ value: StationConfiguration["arrangement"]; label: string }> = [
  { value: "series", label: "Série" },
  { value: "parallel", label: "Parallèle" },
];

export function defaultStationConfiguration(): StationConfiguration {
  return {
    arrangement: "series",
    suction_pressure_min_pa: null,
    discharge_pressure_max_pa: null,
    suction_line_k: 0,
    suction_line_diameter_m: null,
    bypass_k: 0,
    drive_efficiency: 1,
    label: null,
  };
}

/** Payload initial correspondant au type de nœud choisi. */
export function defaultNodePayload(kind: NetworkNode["kind"]): NodePayload {
  if (kind === "station") {
    return defaultStationConfiguration();
  }
  if (kind === "injection" || kind === "offtake") {
    return { flow_m3_s: 0.05 };
  }
  return {};
}

/** Reproduit les bornes que l'API applique au payload d'un nœud. */
export function validateNodePayload(
  kind: NetworkNode["kind"],
  payload: NodePayload,
): string[] {
  if (kind === "injection" || kind === "offtake") {
    const flow = (payload as { flow_m3_s?: number }).flow_m3_s;
    if (flow === undefined || !(flow > 0)) {
      return [
        kind === "injection"
          ? "Le débit injecté doit être strictement positif."
          : "Le débit soutiré doit être strictement positif.",
      ];
    }
    return [];
  }
  if (kind !== "station") {
    return [];
  }
  const station = payload as StationConfiguration;
  const problems: string[] = [];
  if (!(station.drive_efficiency > 0) || station.drive_efficiency > 1) {
    problems.push("Le rendement d'entraînement doit être compris entre 0 exclu et 1.");
  }
  if (station.suction_line_k < 0 || station.bypass_k < 0) {
    problems.push("Les coefficients de perte doivent être positifs ou nuls.");
  }
  if (
    station.suction_pressure_min_pa !== null &&
    station.discharge_pressure_max_pa !== null &&
    station.discharge_pressure_max_pa <= station.suction_pressure_min_pa
  ) {
    problems.push(
      "La pression maximale de refoulement doit dépasser la pression minimale d'aspiration.",
    );
  }
  return problems;
}

interface NodePayloadFormProps {
  kind: NetworkNode["kind"];
  value: NodePayload;
  onChange: (value: NodePayload) => void;
}

export function NodePayloadForm({ kind, value, onChange }: NodePayloadFormProps) {
  if (kind === "station") {
    return (
      <StationFields
        value={value as StationConfiguration}
        onChange={(next) => onChange(next)}
      />
    );
  }

  if (kind === "injection" || kind === "offtake") {
    const flow = (value as { flow_m3_s?: number }).flow_m3_s ?? 0;
    return (
      <fieldset className="field-group">
        <legend>{kind === "injection" ? "Injection" : "Soutirage"}</legend>
        <label>
          {kind === "injection" ? "Débit injecté (m³/h)" : "Débit soutiré (m³/h)"}
          <input
            type="number"
            step="0.1"
            min="0"
            value={String(Number((flow * 3600).toFixed(6)))}
            onChange={(event) =>
              onChange({ flow_m3_s: (parseNumber(event.target.value) ?? 0) / 3600 })
            }
            required
          />
          <small>Le débit est une condition imposée au réseau à ce point.</small>
        </label>
      </fieldset>
    );
  }

  if (kind === "tank") {
    return (
      <p className="field-help">
        Le nœud représente le raccordement d'un bac. Créez le bac et son barémage dans
        « Stockage et transferts », puis renseignez ici l'altitude du piquage.
      </p>
    );
  }

  if (kind === "terminal") {
    return (
      <p className="field-help">
        Le terminal reçoit sa condition aval du scénario : pression de sortie ou niveau de
        bac aval. Aucun paramètre supplémentaire n'est requis sur le nœud.
      </p>
    );
  }

  return (
    <p className="field-help">
      Ce type de nœud n'exige aucun paramètre supplémentaire : l'altitude et les
      coordonnées suffisent au calcul.
    </p>
  );
}

function StationFields({
  value,
  onChange,
}: {
  value: StationConfiguration;
  onChange: (value: StationConfiguration) => void;
}) {
  const update = <K extends keyof StationConfiguration>(
    key: K,
    next: StationConfiguration[K],
  ) => {
    onChange({ ...value, [key]: next });
  };

  return (
    <fieldset className="field-group">
      <legend>Configuration de la station</legend>
      <div className="form-grid three">
        <label>
          Montage des groupes
          <select
            value={value.arrangement}
            onChange={(event) =>
              update("arrangement", event.target.value as StationConfiguration["arrangement"])
            }
          >
            {ARRANGEMENTS.map((arrangement) => (
              <option key={arrangement.value} value={arrangement.value}>
                {arrangement.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Pression d'aspiration minimale (bar abs.)
          <input
            type="number"
            step="0.01"
            min="0"
            value={text(scale(value.suction_pressure_min_pa, 1e-5))}
            onChange={(event) =>
              update("suction_pressure_min_pa", unscale(parseNumber(event.target.value), 1e-5))
            }
          />
        </label>
        <label>
          Pression de refoulement maximale (bar abs.)
          <input
            type="number"
            step="0.01"
            min="0"
            value={text(scale(value.discharge_pressure_max_pa, 1e-5))}
            onChange={(event) =>
              update("discharge_pressure_max_pa", unscale(parseNumber(event.target.value), 1e-5))
            }
          />
        </label>
        <label>
          Diamètre de la ligne d'aspiration (mm)
          <input
            type="number"
            step="1"
            min="0"
            value={text(scale(value.suction_line_diameter_m, 1000))}
            onChange={(event) =>
              update("suction_line_diameter_m", unscale(parseNumber(event.target.value), 1000))
            }
          />
          <small>Nécessaire au contrôle de NPSH disponible.</small>
        </label>
        <label>
          K de la ligne d'aspiration
          <input
            type="number"
            step="0.01"
            min="0"
            value={String(value.suction_line_k)}
            onChange={(event) => update("suction_line_k", parseNumber(event.target.value) ?? 0)}
          />
        </label>
        <label>
          K du bypass
          <input
            type="number"
            step="0.01"
            min="0"
            value={String(value.bypass_k)}
            onChange={(event) => update("bypass_k", parseNumber(event.target.value) ?? 0)}
          />
          <small>Laisser à zéro en l'absence de bypass.</small>
        </label>
        <label>
          Rendement d'entraînement
          <input
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={String(value.drive_efficiency)}
            onChange={(event) => update("drive_efficiency", parseNumber(event.target.value) ?? 1)}
          />
          <small>Moteur et variateur ; 1 pour un entraînement direct idéal.</small>
        </label>
        <label>
          Libellé d'affichage
          <input
            value={value.label ?? ""}
            onChange={(event) => update("label", event.target.value || null)}
          />
        </label>
      </div>
      <p className="field-help">
        Les pompes de la station se posent ensuite comme équipements du nœud, avec leur rôle
        principal ou secours.
      </p>
    </fieldset>
  );
}

function parseNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function text(value: number | null): string {
  return value === null ? "" : String(Number(value.toPrecision(12)));
}

function scale(value: number | null, factor: number): number | null {
  return value === null ? null : value * factor;
}

function unscale(value: number | null, factor: number): number | null {
  return value === null ? null : value / factor;
}
