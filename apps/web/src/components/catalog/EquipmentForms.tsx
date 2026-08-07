/**
 * Fiches structurées des familles documentaires du catalogue.
 *
 * Seules quelques grandeurs alimentent réellement le calcul hydraulique : le
 * coefficient de perte singulière pour une vanne ou un accessoire, la rugosité
 * et la pression maximale admissible pour un matériau. Les autres champs
 * documentent l'équipement pour les rapports et l'exploitation ; ils ne créent
 * aucune conformité normative.
 */

import type { AccessoryPayload, MaterialPayload, ValvePayload } from "../../types";

const VALVE_TYPES: Array<{ value: ValvePayload["valve_type"]; label: string }> = [
  { value: "gate", label: "Vanne à opercule" },
  { value: "globe", label: "Vanne à soupape" },
  { value: "ball", label: "Vanne à boisseau sphérique" },
  { value: "butterfly", label: "Vanne papillon" },
  { value: "check", label: "Clapet anti-retour" },
  { value: "control", label: "Vanne de régulation" },
  { value: "plug", label: "Vanne à boisseau conique" },
  { value: "needle", label: "Vanne à pointeau" },
  { value: "other", label: "Autre type" },
];

const FAIL_POSITIONS: Array<{ value: ValvePayload["fail_position"]; label: string }> = [
  { value: "not_applicable", label: "Sans objet" },
  { value: "fail_open", label: "Ouverte en sécurité" },
  { value: "fail_close", label: "Fermée en sécurité" },
  { value: "fail_last", label: "Maintien de la dernière position" },
];

const ACCESSORY_TYPES: Array<{ value: AccessoryPayload["accessory_type"]; label: string }> = [
  { value: "elbow", label: "Coude" },
  { value: "tee", label: "Té" },
  { value: "reducer", label: "Réduction" },
  { value: "expander", label: "Élargissement" },
  { value: "filter", label: "Filtre" },
  { value: "check_valve", label: "Clapet" },
  { value: "entrance", label: "Entrée" },
  { value: "exit", label: "Sortie" },
  { value: "custom", label: "Accessoire personnalisé" },
];

export function defaultValvePayload(): ValvePayload {
  return {
    valve_type: "gate",
    nominal_diameter_m: null,
    k_coefficient: 0.2,
    cv: null,
    kv: null,
    opening_ratio: 1,
    opening_time_s: null,
    closing_time_s: null,
    fail_position: "not_applicable",
    pressure_class: null,
    manufacturer: null,
    data_source: null,
  };
}

export function defaultMaterialPayload(): MaterialPayload {
  return {
    roughness_m: 4.5e-5,
    mawp_pa: 8e6,
    material_family: null,
    specification: null,
    grade: null,
    smys_pa: null,
    ultimate_strength_pa: null,
    density_kg_m3: null,
    outer_diameter_m: null,
    wall_thickness_m: null,
    corrosion_allowance_m: null,
    design_temperature_k: null,
    standard_reference: null,
    data_source: null,
  };
}

export function defaultAccessoryPayload(): AccessoryPayload {
  return {
    accessory_type: "elbow",
    k_coefficient: 0.3,
    nominal_diameter_m: null,
    equivalent_length_m: null,
    manufacturer: null,
    data_source: null,
  };
}

export function validateValve(payload: ValvePayload): string[] {
  const problems: string[] = [];
  if (payload.k_coefficient === null && payload.cv === null && payload.kv === null) {
    problems.push(
      "Renseignez un coefficient de perte K, ou un Cv/Kv permettant de le déterminer.",
    );
  }
  if (payload.k_coefficient !== null && payload.k_coefficient < 0) {
    problems.push("Le coefficient de perte doit être positif ou nul.");
  }
  return problems;
}

export function validateMaterial(payload: MaterialPayload): string[] {
  const problems: string[] = [];
  if (payload.roughness_m === null) {
    problems.push("La rugosité est obligatoire : elle alimente le calcul de perte de charge.");
  }
  if (
    payload.outer_diameter_m !== null &&
    payload.wall_thickness_m !== null &&
    payload.wall_thickness_m * 2 >= payload.outer_diameter_m
  ) {
    problems.push("L'épaisseur de paroi est incompatible avec le diamètre extérieur.");
  }
  return problems;
}

export function validateAccessory(payload: AccessoryPayload): string[] {
  if (payload.k_coefficient === null && payload.equivalent_length_m === null) {
    return ["Renseignez un coefficient de perte K ou une longueur équivalente."];
  }
  return [];
}

export function ValveForm({
  value,
  onChange,
}: {
  value: ValvePayload;
  onChange: (value: ValvePayload) => void;
}) {
  const update = <K extends keyof ValvePayload>(key: K, next: ValvePayload[K]) => {
    onChange({ ...value, [key]: next });
  };

  return (
    <div className="stack">
      <fieldset className="field-group">
        <legend>Caractéristiques hydrauliques</legend>
        <div className="form-grid three">
          <label>
            Type de vanne
            <select
              value={value.valve_type}
              onChange={(event) =>
                update("valve_type", event.target.value as ValvePayload["valve_type"])
              }
            >
              {VALVE_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Diamètre nominal (mm)
            <input
              type="number"
              step="1"
              min="0"
              value={text(scale(value.nominal_diameter_m, 1000))}
              onChange={(event) =>
                update("nominal_diameter_m", unscale(number(event.target.value), 1000))
              }
            />
          </label>
          <label>
            Coefficient de perte K
            <input
              type="number"
              step="0.01"
              min="0"
              value={text(value.k_coefficient)}
              onChange={(event) => update("k_coefficient", number(event.target.value))}
            />
            <small>Seule grandeur consommée par le calcul hydraulique.</small>
          </label>
          <label>
            Cv
            <input
              type="number"
              step="0.1"
              min="0"
              value={text(value.cv)}
              onChange={(event) => update("cv", number(event.target.value))}
            />
          </label>
          <label>
            Kv
            <input
              type="number"
              step="0.1"
              min="0"
              value={text(value.kv)}
              onChange={(event) => update("kv", number(event.target.value))}
            />
          </label>
          <label>
            Taux d'ouverture nominal
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={String(value.opening_ratio)}
              onChange={(event) => update("opening_ratio", number(event.target.value) ?? 1)}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Manœuvre et sécurité</legend>
        <div className="form-grid three">
          <label>
            Temps d'ouverture (s)
            <input
              type="number"
              step="1"
              min="0"
              value={text(value.opening_time_s)}
              onChange={(event) => update("opening_time_s", number(event.target.value))}
            />
          </label>
          <label>
            Temps de fermeture (s)
            <input
              type="number"
              step="1"
              min="0"
              value={text(value.closing_time_s)}
              onChange={(event) => update("closing_time_s", number(event.target.value))}
            />
          </label>
          <label>
            Position de repli
            <select
              value={value.fail_position}
              onChange={(event) =>
                update("fail_position", event.target.value as ValvePayload["fail_position"])
              }
            >
              {FAIL_POSITIONS.map((position) => (
                <option key={position.value} value={position.value}>
                  {position.label}
                </option>
              ))}
            </select>
            <small>Information d'exploitation : la plateforme ne commande aucun organe.</small>
          </label>
          <label>
            Classe de pression
            <input
              value={value.pressure_class ?? ""}
              onChange={(event) => update("pressure_class", event.target.value || null)}
              placeholder="ANSI 300"
            />
          </label>
          <label>
            Constructeur
            <input
              value={value.manufacturer ?? ""}
              onChange={(event) => update("manufacturer", event.target.value || null)}
            />
          </label>
          <label>
            Origine des données
            <input
              value={value.data_source ?? ""}
              onChange={(event) => update("data_source", event.target.value || null)}
              placeholder="Fiche technique, essai de réception"
            />
          </label>
        </div>
      </fieldset>
    </div>
  );
}

export function MaterialForm({
  value,
  onChange,
}: {
  value: MaterialPayload;
  onChange: (value: MaterialPayload) => void;
}) {
  const update = <K extends keyof MaterialPayload>(key: K, next: MaterialPayload[K]) => {
    onChange({ ...value, [key]: next });
  };

  return (
    <div className="stack">
      <fieldset className="field-group">
        <legend>Grandeurs utilisées par le calcul</legend>
        <div className="form-grid">
          <label>
            Rugosité absolue (mm)
            <input
              type="number"
              step="0.001"
              min="0"
              value={text(scale(value.roughness_m, 1000))}
              onChange={(event) => update("roughness_m", unscale(number(event.target.value), 1000))}
            />
          </label>
          <label>
            Pression maximale admissible (bar)
            <input
              type="number"
              step="0.1"
              min="0"
              value={text(scale(value.mawp_pa, 1e-5))}
              onChange={(event) => update("mawp_pa", unscale(number(event.target.value), 1e-5))}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Identification du matériau</legend>
        <div className="form-grid three">
          <label>
            Famille
            <input
              value={value.material_family ?? ""}
              onChange={(event) => update("material_family", event.target.value || null)}
              placeholder="Acier au carbone"
            />
          </label>
          <label>
            Spécification
            <input
              value={value.specification ?? ""}
              onChange={(event) => update("specification", event.target.value || null)}
              placeholder="API 5L"
            />
          </label>
          <label>
            Grade
            <input
              value={value.grade ?? ""}
              onChange={(event) => update("grade", event.target.value || null)}
              placeholder="X52"
            />
          </label>
          <label>
            Limite d'élasticité SMYS (MPa)
            <input
              type="number"
              step="1"
              min="0"
              value={text(scale(value.smys_pa, 1e-6))}
              onChange={(event) => update("smys_pa", unscale(number(event.target.value), 1e-6))}
            />
          </label>
          <label>
            Résistance ultime (MPa)
            <input
              type="number"
              step="1"
              min="0"
              value={text(scale(value.ultimate_strength_pa, 1e-6))}
              onChange={(event) =>
                update("ultimate_strength_pa", unscale(number(event.target.value), 1e-6))
              }
            />
          </label>
          <label>
            Masse volumique (kg/m³)
            <input
              type="number"
              step="1"
              min="0"
              value={text(value.density_kg_m3)}
              onChange={(event) => update("density_kg_m3", number(event.target.value))}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Géométrie et conception</legend>
        <div className="form-grid three">
          <label>
            Diamètre extérieur (mm)
            <input
              type="number"
              step="0.1"
              min="0"
              value={text(scale(value.outer_diameter_m, 1000))}
              onChange={(event) =>
                update("outer_diameter_m", unscale(number(event.target.value), 1000))
              }
            />
          </label>
          <label>
            Épaisseur nominale (mm)
            <input
              type="number"
              step="0.1"
              min="0"
              value={text(scale(value.wall_thickness_m, 1000))}
              onChange={(event) =>
                update("wall_thickness_m", unscale(number(event.target.value), 1000))
              }
            />
          </label>
          <label>
            Surépaisseur de corrosion (mm)
            <input
              type="number"
              step="0.1"
              min="0"
              value={text(scale(value.corrosion_allowance_m, 1000))}
              onChange={(event) =>
                update("corrosion_allowance_m", unscale(number(event.target.value), 1000))
              }
            />
          </label>
          <label>
            Température de conception (°C)
            <input
              type="number"
              step="1"
              value={text(kelvinToCelsius(value.design_temperature_k))}
              onChange={(event) =>
                update("design_temperature_k", celsiusToKelvin(number(event.target.value)))
              }
            />
          </label>
          <label>
            Référence normative
            <input
              value={value.standard_reference ?? ""}
              onChange={(event) => update("standard_reference", event.target.value || null)}
              placeholder="ASME B31.4, édition retenue"
            />
            <small>Référence documentaire : n'établit aucune conformité.</small>
          </label>
          <label>
            Origine des données
            <input
              value={value.data_source ?? ""}
              onChange={(event) => update("data_source", event.target.value || null)}
            />
          </label>
        </div>
      </fieldset>
    </div>
  );
}

export function AccessoryForm({
  value,
  onChange,
}: {
  value: AccessoryPayload;
  onChange: (value: AccessoryPayload) => void;
}) {
  const update = <K extends keyof AccessoryPayload>(key: K, next: AccessoryPayload[K]) => {
    onChange({ ...value, [key]: next });
  };

  return (
    <fieldset className="field-group">
      <legend>Accessoire de ligne</legend>
      <div className="form-grid three">
        <label>
          Type
          <select
            value={value.accessory_type}
            onChange={(event) =>
              update("accessory_type", event.target.value as AccessoryPayload["accessory_type"])
            }
          >
            {ACCESSORY_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Coefficient de perte K
          <input
            type="number"
            step="0.01"
            min="0"
            value={text(value.k_coefficient)}
            onChange={(event) => update("k_coefficient", number(event.target.value))}
          />
        </label>
        <label>
          Longueur équivalente (m)
          <input
            type="number"
            step="0.1"
            min="0"
            value={text(value.equivalent_length_m)}
            onChange={(event) => update("equivalent_length_m", number(event.target.value))}
          />
          <small>Utile lorsque la source constructeur exprime la perte ainsi.</small>
        </label>
        <label>
          Diamètre nominal (mm)
          <input
            type="number"
            step="1"
            min="0"
            value={text(scale(value.nominal_diameter_m, 1000))}
            onChange={(event) =>
              update("nominal_diameter_m", unscale(number(event.target.value), 1000))
            }
          />
        </label>
        <label>
          Constructeur
          <input
            value={value.manufacturer ?? ""}
            onChange={(event) => update("manufacturer", event.target.value || null)}
          />
        </label>
        <label>
          Origine des données
          <input
            value={value.data_source ?? ""}
            onChange={(event) => update("data_source", event.target.value || null)}
          />
        </label>
      </div>
    </fieldset>
  );
}

function number(value: string): number | null {
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

function kelvinToCelsius(value: number | null): number | null {
  return value === null ? null : Number((value - 273.15).toFixed(3));
}

function celsiusToKelvin(value: number | null): number | null {
  return value === null ? null : value + 273.15;
}
