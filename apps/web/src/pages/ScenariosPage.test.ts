import { describe, expect, it } from "vitest";

import { describeBoundaryConditions } from "./ScenariosPage";
import type { ScenarioPayload } from "../types";

const BASE: ScenarioPayload = {
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

describe("contraintes du scénario", () => {
  it("refuse un problème sans condition", () => {
    const verdict = describeBoundaryConditions(BASE, false);

    expect(verdict.valid).toBe(false);
    expect(verdict.message).toContain("sous-contraint");
  });

  it("accepte un débit imposé avec une pression amont", () => {
    const verdict = describeBoundaryConditions(
      { ...BASE, imposed_flow_m3_s: 0.2, inlet_pressure_pa: 5_000_000 },
      false,
    );

    expect(verdict.valid).toBe(true);
  });

  it("accepte deux conditions d'extrémité sans débit", () => {
    const verdict = describeBoundaryConditions(
      { ...BASE, inlet_pressure_pa: 5_000_000, outlet_pressure_pa: 200_000 },
      false,
    );

    expect(verdict.valid).toBe(true);
    expect(verdict.message).toContain("recherche le débit");
  });

  it("refuse un problème sur-contraint", () => {
    const verdict = describeBoundaryConditions(
      {
        ...BASE,
        imposed_flow_m3_s: 0.2,
        inlet_pressure_pa: 5_000_000,
        outlet_pressure_pa: 200_000,
      },
      false,
    );

    expect(verdict.valid).toBe(false);
    expect(verdict.message).toContain("sur-contraint");
  });

  it("n'accepte un niveau de bac que si le modèle en comporte un", () => {
    const payload = { ...BASE, imposed_flow_m3_s: 0.2, inlet_tank_level_m: 12 };

    expect(describeBoundaryConditions(payload, false).valid).toBe(false);
    expect(describeBoundaryConditions(payload, true).valid).toBe(true);
  });
});
