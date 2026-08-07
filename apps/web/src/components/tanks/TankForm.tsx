import { useState } from "react";

import type { StrappingPoint, TankDraft, TankLevels } from "../../types";

const TANK_TYPES: Array<{ value: TankDraft["tank_type"]; label: string }> = [
  { value: "vertical_fixed_roof", label: "Vertical à toit fixe" },
  { value: "floating_roof", label: "Toit flottant" },
  { value: "horizontal", label: "Horizontal" },
  { value: "sphere", label: "Sphère" },
  { value: "custom", label: "Autre géométrie" },
];

const STATUSES: Array<{ value: TankDraft["status"]; label: string }> = [
  { value: "available", label: "Disponible" },
  { value: "unavailable", label: "Indisponible" },
  { value: "maintenance", label: "En maintenance" },
  { value: "bypassed", label: "Contourné" },
];

/**
 * Barémage linéaire calculé depuis une hauteur et une capacité.
 *
 * Le code du moteur le réserve explicitement aux études et aux tests : il ne
 * remplace pas une table de jaugeage certifiée (ISO 7507).
 */
export function theoreticalStrapping(heightM: number, capacityM3: number): StrappingPoint[] {
  return [
    { height_m: 0, volume_m3: 0 },
    { height_m: heightM, volume_m3: capacityM3 },
  ];
}

export function defaultLevels(heightM: number): TankLevels {
  return {
    minimum_m: round(heightM * 0.05),
    low_m: round(heightM * 0.1),
    normal_m: round(heightM * 0.5),
    high_m: round(heightM * 0.9),
    high_high_m: round(heightM * 0.95),
  };
}

export function defaultTankDraft(): TankDraft {
  const height = 12;
  return {
    name: "",
    code: "",
    tank_type: "vertical_fixed_roof",
    elevation_m: 0,
    current_level_m: 6,
    fluid_id: null,
    compatible_fluid_ids: [],
    status: "available",
    dead_volume_m3: 0,
    levels: defaultLevels(height),
    strapping: theoreticalStrapping(height, 10000),
    strapping_origin: "theoretical",
  };
}

/**
 * Reproduit les contrôles que l'API applique au bac : ordre des seuils, table de
 * barémage croissante, niveau courant dans le domaine barémé.
 */
export function validateTank(draft: TankDraft): string[] {
  const problems: string[] = [];
  if (!draft.name.trim() || !draft.code.trim()) {
    problems.push("Le nom et le code du bac sont obligatoires.");
  }
  if (draft.strapping.length < 2) {
    problems.push("Le barémage doit comporter au moins deux points.");
  }
  const increasing = draft.strapping.every(
    (point, index) =>
      index === 0 ||
      (point.height_m > draft.strapping[index - 1].height_m &&
        point.volume_m3 >= draft.strapping[index - 1].volume_m3),
  );
  if (!increasing) {
    problems.push(
      "Le barémage doit être strictement croissant en hauteur et non décroissant en volume.",
    );
  }

  const top = draft.strapping[draft.strapping.length - 1]?.height_m ?? 0;
  if (draft.current_level_m > top) {
    problems.push("Le niveau courant dépasse la hauteur barémée du bac.");
  }
  if (draft.levels.high_high_m > top) {
    problems.push("Le seuil très haut dépasse la hauteur barémée du bac.");
  }

  const ordered = [
    draft.levels.minimum_m,
    draft.levels.low_m,
    draft.levels.normal_m,
    draft.levels.high_m,
    draft.levels.high_high_m,
  ].filter((value): value is number => value !== null);
  const monotone = ordered.every((value, index) => index === 0 || value >= ordered[index - 1]);
  if (!monotone) {
    problems.push("Les seuils doivent être ordonnés du minimum au très haut.");
  }
  return problems;
}

interface TankFormProps {
  value: TankDraft;
  onChange: (value: TankDraft) => void;
}

export function TankForm({ value, onChange }: TankFormProps) {
  const [height, setHeight] = useState("12");
  const [capacity, setCapacity] = useState("10000");

  const update = <K extends keyof TankDraft>(key: K, next: TankDraft[K]) => {
    onChange({ ...value, [key]: next });
  };
  const updateLevel = <K extends keyof TankLevels>(key: K, next: TankLevels[K]) => {
    onChange({ ...value, levels: { ...value.levels, [key]: next } });
  };

  const applyTheoretical = () => {
    const heightM = parseNumber(height) ?? 12;
    const capacityM3 = parseNumber(capacity) ?? 10000;
    onChange({
      ...value,
      strapping: theoreticalStrapping(heightM, capacityM3),
      levels: defaultLevels(heightM),
      strapping_origin: "theoretical",
    });
  };

  return (
    <div className="stack">
      <fieldset className="field-group">
        <legend>Identification</legend>
        <div className="form-grid three">
          <label>
            Nom
            <input value={value.name} onChange={(event) => update("name", event.target.value)} required />
          </label>
          <label>
            Code
            <input
              value={value.code}
              onChange={(event) => update("code", event.target.value.toUpperCase())}
              required
            />
          </label>
          <label>
            Type de bac
            <select
              value={value.tank_type}
              onChange={(event) => update("tank_type", event.target.value as TankDraft["tank_type"])}
            >
              {TANK_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Altitude du fond (m)
            <input
              type="number"
              step="any"
              value={String(value.elevation_m)}
              onChange={(event) => update("elevation_m", parseNumber(event.target.value) ?? 0)}
            />
          </label>
          <label>
            État
            <select
              value={value.status}
              onChange={(event) => update("status", event.target.value as TankDraft["status"])}
            >
              {STATUSES.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Volume mort (m³)
            <input
              type="number"
              step="any"
              min="0"
              value={String(value.dead_volume_m3)}
              onChange={(event) => update("dead_volume_m3", parseNumber(event.target.value) ?? 0)}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Produit</legend>
        <div className="form-grid">
          <label>
            Produit courant
            <input
              value={value.fluid_id ?? ""}
              onChange={(event) => update("fluid_id", event.target.value || null)}
              placeholder="diesel"
            />
          </label>
          <label>
            Produits compatibles
            <input
              value={value.compatible_fluid_ids.join(", ")}
              onChange={(event) =>
                update(
                  "compatible_fluid_ids",
                  event.target.value
                    .split(",")
                    .map((item) => item.trim())
                    .filter(Boolean),
                )
              }
              placeholder="diesel, kerosene"
            />
          </label>
          <label>
            Niveau courant (m)
            <input
              type="number"
              step="any"
              min="0"
              value={String(value.current_level_m)}
              onChange={(event) => update("current_level_m", parseNumber(event.target.value) ?? 0)}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Seuils d'exploitation</legend>
        <div className="form-grid three">
          <label>
            Minimum (m)
            <input
              type="number"
              step="any"
              min="0"
              value={String(value.levels.minimum_m)}
              onChange={(event) => updateLevel("minimum_m", parseNumber(event.target.value) ?? 0)}
            />
          </label>
          <label>
            Bas (m)
            <input
              type="number"
              step="any"
              min="0"
              value={levelValue(value.levels.low_m)}
              onChange={(event) => updateLevel("low_m", parseNumber(event.target.value))}
            />
          </label>
          <label>
            Normal (m)
            <input
              type="number"
              step="any"
              min="0"
              value={levelValue(value.levels.normal_m)}
              onChange={(event) => updateLevel("normal_m", parseNumber(event.target.value))}
            />
          </label>
          <label>
            Haut (m)
            <input
              type="number"
              step="any"
              min="0"
              value={levelValue(value.levels.high_m)}
              onChange={(event) => updateLevel("high_m", parseNumber(event.target.value))}
            />
          </label>
          <label>
            Très haut (m)
            <input
              type="number"
              step="any"
              min="0"
              value={String(value.levels.high_high_m)}
              onChange={(event) =>
                updateLevel("high_high_m", parseNumber(event.target.value) ?? 1)
              }
            />
          </label>
        </div>
        <p className="field-help">
          Ces seuils déclenchent l'arrêt des transferts. Ils ne constituent pas à eux seuls un
          dispositif de prévention de débordement au sens d'API 2350.
        </p>
      </fieldset>

      <fieldset className="field-group">
        <legend>Barémage</legend>
        <div className="form-grid three">
          <label>
            Hauteur barémée (m)
            <input
              type="number"
              step="any"
              min="0.1"
              value={height}
              onChange={(event) => setHeight(event.target.value)}
            />
          </label>
          <label>
            Capacité correspondante (m³)
            <input
              type="number"
              step="any"
              min="1"
              value={capacity}
              onChange={(event) => setCapacity(event.target.value)}
            />
          </label>
          <label>
            Origine de la table
            <select
              value={value.strapping_origin}
              onChange={(event) =>
                update("strapping_origin", event.target.value as TankDraft["strapping_origin"])
              }
            >
              <option value="theoretical">Théorique — étude et essais</option>
              <option value="certified">Jaugeage certifié — saisie point par point</option>
            </select>
          </label>
        </div>

        <div className="button-row">
          <button type="button" className="button button-ghost" onClick={applyTheoretical}>
            Générer un barémage théorique linéaire
          </button>
          <button
            type="button"
            className="button button-ghost"
            onClick={() =>
              onChange({
                ...value,
                strapping_origin: "certified",
                strapping: [
                  ...value.strapping,
                  {
                    height_m:
                      (value.strapping[value.strapping.length - 1]?.height_m ?? 0) + 1,
                    volume_m3: value.strapping[value.strapping.length - 1]?.volume_m3 ?? 0,
                  },
                ],
              })
            }
          >
            Ajouter un point de jaugeage
          </button>
        </div>

        {value.strapping_origin === "theoretical" ? (
          <div className="notice" role="note">
            Barémage théorique : réservé aux études et aux essais. Il ne remplace pas une table de
            jaugeage certifiée établie selon ISO 7507, et ne doit pas servir à un mouvement
            commercial.
          </div>
        ) : null}

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Hauteur (m)</th>
                <th>Volume (m³)</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {value.strapping.map((point, index) => (
                <tr key={index}>
                  <td>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={String(point.height_m)}
                      onChange={(event) =>
                        update(
                          "strapping",
                          replacePoint(value.strapping, index, {
                            height_m: parseNumber(event.target.value) ?? 0,
                          }),
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={String(point.volume_m3)}
                      onChange={(event) =>
                        update(
                          "strapping",
                          replacePoint(value.strapping, index, {
                            volume_m3: parseNumber(event.target.value) ?? 0,
                          }),
                        )
                      }
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="button button-ghost"
                      disabled={value.strapping.length <= 2}
                      onClick={() =>
                        update(
                          "strapping",
                          value.strapping.filter((_, current) => current !== index),
                        )
                      }
                    >
                      Retirer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </fieldset>
    </div>
  );
}

function replacePoint(
  points: StrappingPoint[],
  index: number,
  patch: Partial<StrappingPoint>,
): StrappingPoint[] {
  return points.map((point, current) => (current === index ? { ...point, ...patch } : point));
}

function parseNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function levelValue(value: number | null): string {
  return value === null ? "" : String(value);
}

function round(value: number): number {
  return Number(value.toFixed(3));
}
