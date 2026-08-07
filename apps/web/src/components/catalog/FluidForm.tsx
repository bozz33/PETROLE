import type { FluidPayload, PropertyPoint, PropertyTable } from "../../types";

/** Catégories de produits gérées par le MVP, dans l'ordre du dictionnaire de données. */
const CATEGORIES: Array<{ value: FluidPayload["category"]; label: string }> = [
  { value: "crude", label: "Brut" },
  { value: "gasoline", label: "Essence" },
  { value: "diesel", label: "Gazole" },
  { value: "kerosene", label: "Kérosène" },
  { value: "fuel_oil_light", label: "Fioul léger" },
  { value: "fuel_oil_heavy", label: "Fioul lourd" },
  { value: "condensate", label: "Condensat" },
  { value: "water", label: "Eau" },
  { value: "custom", label: "Autre produit" },
];

const SOURCES: Array<{ value: PropertyTable["source"]; label: string }> = [
  { value: "laboratory", label: "Analyse de laboratoire" },
  { value: "internal_table", label: "Table interne" },
  { value: "correlation", label: "Corrélation" },
  { value: "coolprop", label: "CoolProp" },
  { value: "constant", label: "Valeur constante" },
];

const QUALITIES: Array<{ value: PropertyPoint["quality"]; label: string }> = [
  { value: "measured", label: "Mesurée" },
  { value: "approved", label: "Approuvée" },
  { value: "estimated", label: "Estimée" },
  { value: "extrapolated", label: "Extrapolée" },
];

/** Table vide prête à l'édition : le moteur exige au moins deux points. */
export function emptyPropertyTable(): PropertyTable {
  return {
    points: [
      { temperature_k: 288.15, value: 0, pressure_pa: 101325, uncertainty: null, method: null, quality: "measured" },
      { temperature_k: 313.15, value: 0, pressure_pa: 101325, uncertainty: null, method: null, quality: "measured" },
    ],
    source: "laboratory",
    reference: null,
  };
}

export function defaultFluidPayload(): FluidPayload {
  return {
    category: "custom",
    reference_temperature_k: 288.15,
    reference_pressure_pa: 101325,
    density_kg_m3: 840,
    kinematic_viscosity_m2_s: 4e-6,
    vapor_pressure_pa: 5000,
    density_table: null,
    kinematic_viscosity_table: null,
    vapor_pressure_table: null,
    thermal_expansion_1_k: null,
    coolprop_name: null,
    data_source: null,
    batch_reference: null,
  };
}

/**
 * Vérifie, avant l'appel réseau, les deux règles que le moteur applique de son
 * côté : une source de masse volumique et des tables strictement croissantes.
 */
export function validateFluid(payload: FluidPayload): string[] {
  const problems: string[] = [];
  if (payload.density_kg_m3 === null && payload.density_table === null) {
    problems.push(
      "Renseignez une masse volumique constante ou une table température–masse volumique.",
    );
  }
  const tables: Array<[string, PropertyTable | null]> = [
    ["masse volumique", payload.density_table],
    ["viscosité cinématique", payload.kinematic_viscosity_table],
    ["pression de vapeur", payload.vapor_pressure_table],
  ];
  for (const [label, table] of tables) {
    if (!table) {
      continue;
    }
    if (table.points.length < 2) {
      problems.push(`La table de ${label} doit comporter au moins deux points.`);
      continue;
    }
    const increasing = table.points.every(
      (point, index) => index === 0 || point.temperature_k > table.points[index - 1].temperature_k,
    );
    if (!increasing) {
      problems.push(`Les températures de la table de ${label} doivent être strictement croissantes.`);
    }
  }
  return problems;
}

interface FluidFormProps {
  value: FluidPayload;
  onChange: (value: FluidPayload) => void;
}

export function FluidForm({ value, onChange }: FluidFormProps) {
  const update = <K extends keyof FluidPayload>(key: K, next: FluidPayload[K]) => {
    onChange({ ...value, [key]: next });
  };

  return (
    <div className="stack">
      <fieldset className="field-group">
        <legend>Conditions de référence</legend>
        <div className="form-grid three">
          <label>
            Catégorie de produit
            <select
              value={value.category}
              onChange={(event) => update("category", event.target.value as FluidPayload["category"])}
            >
              {CATEGORIES.map((category) => (
                <option key={category.value} value={category.value}>
                  {category.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Température de référence (°C)
            <input
              type="number"
              step="0.01"
              value={toCelsius(value.reference_temperature_k)}
              onChange={(event) =>
                update("reference_temperature_k", fromCelsius(event.target.value) ?? 288.15)
              }
            />
          </label>
          <label>
            Pression de référence (bar abs.)
            <input
              type="number"
              step="0.0001"
              min="0"
              value={String(value.reference_pressure_pa / 100000)}
              onChange={(event) =>
                update("reference_pressure_pa", (parseNumber(event.target.value) ?? 1.01325) * 100000)
              }
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Propriétés aux conditions de référence</legend>
        <div className="form-grid three">
          <label>
            Masse volumique (kg/m³)
            <input
              type="number"
              step="0.1"
              min="0"
              value={inputValue(value.density_kg_m3)}
              onChange={(event) => update("density_kg_m3", parseNumber(event.target.value))}
            />
            <small>Obligatoire si aucune table de masse volumique n'est fournie.</small>
          </label>
          <label>
            Viscosité cinématique (cSt)
            <input
              type="number"
              step="0.001"
              min="0"
              value={inputValue(scale(value.kinematic_viscosity_m2_s, 1e6))}
              onChange={(event) =>
                update("kinematic_viscosity_m2_s", unscale(parseNumber(event.target.value), 1e6))
              }
            />
            <small>1 cSt = 10⁻⁶ m²/s.</small>
          </label>
          <label>
            Pression de vapeur (bar abs.)
            <input
              type="number"
              step="0.0001"
              min="0"
              value={inputValue(scale(value.vapor_pressure_pa, 1e-5))}
              onChange={(event) =>
                update("vapor_pressure_pa", unscale(parseNumber(event.target.value), 1e-5))
              }
            />
            <small>Utilisée par le contrôle de cavitation.</small>
          </label>
          <label>
            Dilatation thermique (1/K)
            <input
              type="number"
              step="0.00001"
              value={inputValue(value.thermal_expansion_1_k)}
              onChange={(event) => update("thermal_expansion_1_k", parseNumber(event.target.value))}
            />
          </label>
          <label>
            Identifiant CoolProp
            <input
              value={value.coolprop_name ?? ""}
              onChange={(event) => update("coolprop_name", event.target.value || null)}
              placeholder="Par exemple n-Dodecane"
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Traçabilité de la donnée</legend>
        <div className="form-grid">
          <label>
            Origine des données
            <input
              value={value.data_source ?? ""}
              onChange={(event) => update("data_source", event.target.value || null)}
              placeholder="Laboratoire, méthode d'essai et date d'analyse"
            />
          </label>
          <label>
            Lot ou référence produit
            <input
              value={value.batch_reference ?? ""}
              onChange={(event) => update("batch_reference", event.target.value || null)}
            />
          </label>
        </div>
      </fieldset>

      <PropertyTableEditor
        legend="Table température → masse volumique (kg/m³)"
        table={value.density_table}
        onChange={(table) => update("density_table", table)}
      />
      <PropertyTableEditor
        legend="Table température → viscosité cinématique (m²/s)"
        table={value.kinematic_viscosity_table}
        onChange={(table) => update("kinematic_viscosity_table", table)}
      />
      <PropertyTableEditor
        legend="Table température → pression de vapeur (Pa)"
        table={value.vapor_pressure_table}
        onChange={(table) => update("vapor_pressure_table", table)}
      />
    </div>
  );
}

interface PropertyTableEditorProps {
  legend: string;
  table: PropertyTable | null;
  onChange: (table: PropertyTable | null) => void;
}

function PropertyTableEditor({ legend, table, onChange }: PropertyTableEditorProps) {
  if (!table) {
    return (
      <fieldset className="field-group">
        <legend>{legend}</legend>
        <p className="field-help">
          Aucune table : la valeur constante des conditions de référence est utilisée.
        </p>
        <div className="button-row">
          <button
            type="button"
            className="button button-ghost"
            onClick={() => onChange(emptyPropertyTable())}
          >
            Ajouter une table mesurée
          </button>
        </div>
      </fieldset>
    );
  }

  const updatePoint = (index: number, patch: Partial<PropertyPoint>) => {
    onChange({
      ...table,
      points: table.points.map((point, current) =>
        current === index ? { ...point, ...patch } : point,
      ),
    });
  };

  return (
    <fieldset className="field-group">
      <legend>{legend}</legend>
      <div className="form-grid">
        <label>
          Origine de la table
          <select
            value={table.source}
            onChange={(event) =>
              onChange({ ...table, source: event.target.value as PropertyTable["source"] })
            }
          >
            {SOURCES.map((source) => (
              <option key={source.value} value={source.value}>
                {source.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Référence du document
          <input
            value={table.reference ?? ""}
            onChange={(event) => onChange({ ...table, reference: event.target.value || null })}
            placeholder="Rapport d'analyse, norme d'essai"
          />
        </label>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Température (°C)</th>
              <th>Valeur</th>
              <th>Pression (bar abs.)</th>
              <th>Incertitude</th>
              <th>Méthode</th>
              <th>Qualité</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {table.points.map((point, index) => (
              <tr key={index}>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    value={toCelsius(point.temperature_k)}
                    onChange={(event) =>
                      updatePoint(index, {
                        temperature_k: fromCelsius(event.target.value) ?? point.temperature_k,
                      })
                    }
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="any"
                    value={String(point.value)}
                    onChange={(event) =>
                      updatePoint(index, { value: parseNumber(event.target.value) ?? 0 })
                    }
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.0001"
                    min="0"
                    value={String(point.pressure_pa / 100000)}
                    onChange={(event) =>
                      updatePoint(index, {
                        pressure_pa: (parseNumber(event.target.value) ?? 1.01325) * 100000,
                      })
                    }
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={inputValue(point.uncertainty)}
                    onChange={(event) =>
                      updatePoint(index, { uncertainty: parseNumber(event.target.value) })
                    }
                  />
                </td>
                <td>
                  <input
                    value={point.method ?? ""}
                    onChange={(event) => updatePoint(index, { method: event.target.value || null })}
                    placeholder="ASTM D1298"
                  />
                </td>
                <td>
                  <select
                    value={point.quality}
                    onChange={(event) =>
                      updatePoint(index, { quality: event.target.value as PropertyPoint["quality"] })
                    }
                  >
                    {QUALITIES.map((quality) => (
                      <option key={quality.value} value={quality.value}>
                        {quality.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <button
                    type="button"
                    className="button button-ghost"
                    disabled={table.points.length <= 2}
                    onClick={() =>
                      onChange({
                        ...table,
                        points: table.points.filter((_, current) => current !== index),
                      })
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

      <div className="button-row">
        <button
          type="button"
          className="button button-ghost"
          onClick={() =>
            onChange({
              ...table,
              points: [
                ...table.points,
                {
                  temperature_k:
                    (table.points[table.points.length - 1]?.temperature_k ?? 288.15) + 10,
                  value: table.points[table.points.length - 1]?.value ?? 0,
                  pressure_pa: 101325,
                  uncertainty: null,
                  method: null,
                  quality: "measured",
                },
              ],
            })
          }
        >
          Ajouter un point
        </button>
        <button type="button" className="button button-ghost" onClick={() => onChange(null)}>
          Supprimer la table
        </button>
      </div>
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

function inputValue(value: number | null): string {
  return value === null ? "" : String(value);
}

function scale(value: number | null, factor: number): number | null {
  return value === null ? null : value * factor;
}

function unscale(value: number | null, factor: number): number | null {
  return value === null ? null : value / factor;
}

function toCelsius(kelvin: number): string {
  return String(Number((kelvin - 273.15).toFixed(4)));
}

function fromCelsius(value: string): number | null {
  const parsed = parseNumber(value);
  return parsed === null ? null : parsed + 273.15;
}
