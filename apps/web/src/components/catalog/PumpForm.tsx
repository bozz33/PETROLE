import type { PumpPayload } from "../../types";

export function defaultPumpPayload(): PumpPayload {
  return {
    curve: {
      flows_m3_s: [0.1, 0.2, 0.3],
      heads_m: [210, 185, 145],
      efficiencies: [0.72, 0.82, 0.76],
      powers_w: null,
      npshr_m: [3.5, 4.5, 6],
      reference_speed_rpm: 3000,
      interpolation: "pchip",
    },
    manufacturer: null,
    motor_rated_power_w: null,
    npsh_margin_m: 0.5,
    min_speed_ratio: 0.7,
    max_speed_ratio: 1,
    minimum_continuous_flow_m3_s: null,
    data_source: null,
  };
}

/**
 * Applique les règles que le moteur vérifie sur une courbe constructeur : au
 * moins deux points, séries optionnelles de même longueur, débits croissants.
 */
export function validatePump(payload: PumpPayload): string[] {
  const problems: string[] = [];
  const { curve } = payload;
  const count = curve.flows_m3_s.length;

  if (count < 2) {
    problems.push("La courbe doit comporter au moins deux points.");
  }
  if (curve.heads_m.length !== count) {
    problems.push("Chaque débit doit avoir une hauteur associée.");
  }
  const paired: Array<[string, number[] | null]> = [
    ["rendement", curve.efficiencies],
    ["puissance", curve.powers_w],
    ["NPSH requis", curve.npshr_m],
  ];
  for (const [label, series] of paired) {
    if (series && series.length !== count) {
      problems.push(`La série de ${label} doit comporter ${String(count)} points.`);
    }
  }
  const increasing = curve.flows_m3_s.every(
    (flow, index) => index === 0 || flow > curve.flows_m3_s[index - 1],
  );
  if (!increasing) {
    problems.push("Les débits de la courbe doivent être strictement croissants.");
  }
  if (payload.max_speed_ratio < payload.min_speed_ratio) {
    problems.push("Le rapport de vitesse maximal doit être supérieur au minimal.");
  }
  return problems;
}

interface PumpFormProps {
  value: PumpPayload;
  onChange: (value: PumpPayload) => void;
}

export function PumpForm({ value, onChange }: PumpFormProps) {
  const { curve } = value;
  const pointCount = curve.flows_m3_s.length;

  const update = <K extends keyof PumpPayload>(key: K, next: PumpPayload[K]) => {
    onChange({ ...value, [key]: next });
  };
  const updateCurve = <K extends keyof PumpPayload["curve"]>(
    key: K,
    next: PumpPayload["curve"][K],
  ) => {
    onChange({ ...value, curve: { ...curve, [key]: next } });
  };

  const setSeriesValue = (
    key: "flows_m3_s" | "heads_m" | "efficiencies" | "powers_w" | "npshr_m",
    index: number,
    raw: string,
  ) => {
    const parsed = parseNumber(raw) ?? 0;
    const series = key === "flows_m3_s" || key === "heads_m" ? curve[key] : curve[key];
    if (!series) {
      return;
    }
    updateCurve(
      key,
      series.map((item, current) => (current === index ? parsed : item)) as never,
    );
  };

  const toggleSeries = (key: "efficiencies" | "powers_w" | "npshr_m") => {
    updateCurve(key, curve[key] ? null : (Array.from({ length: pointCount }, () => 0) as never));
  };

  return (
    <div className="stack">
      <fieldset className="field-group">
        <legend>Courbe constructeur</legend>
        <div className="form-grid three">
          <label>
            Vitesse de référence (tr/min)
            <input
              type="number"
              step="1"
              min="0"
              value={inputValue(curve.reference_speed_rpm)}
              onChange={(event) =>
                updateCurve("reference_speed_rpm", parseNumber(event.target.value))
              }
            />
          </label>
          <label>
            Interpolation
            <select
              value={curve.interpolation}
              onChange={(event) =>
                updateCurve("interpolation", event.target.value as "linear" | "pchip")
              }
            >
              <option value="pchip">Monotone (pchip)</option>
              <option value="linear">Linéaire</option>
            </select>
          </label>
          <label>
            Origine de la courbe
            <input
              value={value.data_source ?? ""}
              onChange={(event) => update("data_source", event.target.value || null)}
              placeholder="Courbe certifiée, essai de réception"
            />
          </label>
        </div>

        <div className="button-row">
          <button type="button" className="button button-ghost" onClick={() => toggleSeries("efficiencies")}>
            {curve.efficiencies ? "Retirer le rendement" : "Ajouter le rendement η(Q)"}
          </button>
          <button type="button" className="button button-ghost" onClick={() => toggleSeries("powers_w")}>
            {curve.powers_w ? "Retirer la puissance" : "Ajouter la puissance P(Q)"}
          </button>
          <button type="button" className="button button-ghost" onClick={() => toggleSeries("npshr_m")}>
            {curve.npshr_m ? "Retirer le NPSH requis" : "Ajouter le NPSH requis"}
          </button>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Débit (m³/h)</th>
                <th>Hauteur (m)</th>
                {curve.efficiencies ? <th>Rendement</th> : null}
                {curve.powers_w ? <th>Puissance (kW)</th> : null}
                {curve.npshr_m ? <th>NPSHr (m)</th> : null}
                <th />
              </tr>
            </thead>
            <tbody>
              {curve.flows_m3_s.map((flow, index) => (
                <tr key={index}>
                  <td>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={String(Number((flow * 3600).toFixed(6)))}
                      onChange={(event) =>
                        setSeriesValue(
                          "flows_m3_s",
                          index,
                          String((parseNumber(event.target.value) ?? 0) / 3600),
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.1"
                      value={String(curve.heads_m[index] ?? 0)}
                      onChange={(event) => setSeriesValue("heads_m", index, event.target.value)}
                    />
                  </td>
                  {curve.efficiencies ? (
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max="1"
                        value={String(curve.efficiencies[index] ?? 0)}
                        onChange={(event) =>
                          setSeriesValue("efficiencies", index, event.target.value)
                        }
                      />
                    </td>
                  ) : null}
                  {curve.powers_w ? (
                    <td>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={String((curve.powers_w[index] ?? 0) / 1000)}
                        onChange={(event) =>
                          setSeriesValue(
                            "powers_w",
                            index,
                            String((parseNumber(event.target.value) ?? 0) * 1000),
                          )
                        }
                      />
                    </td>
                  ) : null}
                  {curve.npshr_m ? (
                    <td>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={String(curve.npshr_m[index] ?? 0)}
                        onChange={(event) => setSeriesValue("npshr_m", index, event.target.value)}
                      />
                    </td>
                  ) : null}
                  <td>
                    <button
                      type="button"
                      className="button button-ghost"
                      disabled={pointCount <= 2}
                      onClick={() => onChange({ ...value, curve: removePoint(curve, index) })}
                    >
                      Retirer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="button-row">
          <button
            type="button"
            className="button button-ghost"
            onClick={() => onChange({ ...value, curve: appendPoint(curve) })}
          >
            Ajouter un point
          </button>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Limites d'exploitation et moteur</legend>
        <div className="form-grid three">
          <label>
            Constructeur
            <input
              value={value.manufacturer ?? ""}
              onChange={(event) => update("manufacturer", event.target.value || null)}
            />
          </label>
          <label>
            Puissance nominale du moteur (kW)
            <input
              type="number"
              step="0.1"
              min="0"
              value={inputValue(divide(value.motor_rated_power_w, 1000))}
              onChange={(event) =>
                update("motor_rated_power_w", multiply(parseNumber(event.target.value), 1000))
              }
            />
            <small>Utilisée par le contrôle de surcharge moteur.</small>
          </label>
          <label>
            Marge de NPSH (m)
            <input
              type="number"
              step="0.1"
              min="0"
              value={String(value.npsh_margin_m)}
              onChange={(event) => update("npsh_margin_m", parseNumber(event.target.value) ?? 0.5)}
            />
          </label>
          <label>
            Rapport de vitesse minimal
            <input
              type="number"
              step="0.01"
              min="0"
              value={String(value.min_speed_ratio)}
              onChange={(event) => update("min_speed_ratio", parseNumber(event.target.value) ?? 0.7)}
            />
          </label>
          <label>
            Rapport de vitesse maximal
            <input
              type="number"
              step="0.01"
              min="0"
              value={String(value.max_speed_ratio)}
              onChange={(event) => update("max_speed_ratio", parseNumber(event.target.value) ?? 1)}
            />
          </label>
          <label>
            Débit minimal continu (m³/h)
            <input
              type="number"
              step="0.1"
              min="0"
              value={inputValue(multiply(value.minimum_continuous_flow_m3_s, 3600))}
              onChange={(event) =>
                update(
                  "minimum_continuous_flow_m3_s",
                  divide(parseNumber(event.target.value), 3600),
                )
              }
            />
          </label>
        </div>
      </fieldset>
    </div>
  );
}

function appendPoint(curve: PumpPayload["curve"]): PumpPayload["curve"] {
  const lastFlow = curve.flows_m3_s[curve.flows_m3_s.length - 1] ?? 0;
  const lastHead = curve.heads_m[curve.heads_m.length - 1] ?? 0;
  return {
    ...curve,
    flows_m3_s: [...curve.flows_m3_s, lastFlow + 0.05],
    heads_m: [...curve.heads_m, lastHead],
    efficiencies: curve.efficiencies ? [...curve.efficiencies, 0] : null,
    powers_w: curve.powers_w ? [...curve.powers_w, 0] : null,
    npshr_m: curve.npshr_m ? [...curve.npshr_m, 0] : null,
  };
}

function removePoint(curve: PumpPayload["curve"], index: number): PumpPayload["curve"] {
  const without = <T,>(series: T[]) => series.filter((_, current) => current !== index);
  return {
    ...curve,
    flows_m3_s: without(curve.flows_m3_s),
    heads_m: without(curve.heads_m),
    efficiencies: curve.efficiencies ? without(curve.efficiencies) : null,
    powers_w: curve.powers_w ? without(curve.powers_w) : null,
    npshr_m: curve.npshr_m ? without(curve.npshr_m) : null,
  };
}

function parseNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function inputValue(value: number | null): string {
  return value === null ? "" : String(value);
}

function multiply(value: number | null, factor: number): number | null {
  return value === null ? null : value * factor;
}

function divide(value: number | null, factor: number): number | null {
  return value === null ? null : value / factor;
}
