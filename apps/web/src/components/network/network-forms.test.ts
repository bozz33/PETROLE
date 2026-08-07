import { describe, expect, it } from "vitest";

import {
  defaultEdgeGeometry,
  defaultProfile,
  validateEdgeDetails,
} from "./EdgeDetailsForm";
import { defaultNodePayload, validateNodePayload } from "./NodePayloadForm";
import type { StationConfiguration } from "../../types";

describe("payload de nœud", () => {
  it("n'exige rien pour une jonction", () => {
    expect(validateNodePayload("junction", defaultNodePayload("junction"))).toEqual([]);
  });

  it("exige un débit strictement positif pour une injection", () => {
    expect(validateNodePayload("injection", { flow_m3_s: 0 })).toHaveLength(1);
    expect(validateNodePayload("injection", { flow_m3_s: 0.05 })).toEqual([]);
  });

  it("accepte la configuration de station par défaut", () => {
    expect(validateNodePayload("station", defaultNodePayload("station"))).toEqual([]);
  });

  it("refuse un rendement d'entraînement hors bornes", () => {
    const station = defaultNodePayload("station") as StationConfiguration;

    expect(validateNodePayload("station", { ...station, drive_efficiency: 0 })).toHaveLength(1);
    expect(validateNodePayload("station", { ...station, drive_efficiency: 1.2 })).toHaveLength(1);
  });

  it("refuse un refoulement maximal sous l'aspiration minimale", () => {
    const station = defaultNodePayload("station") as StationConfiguration;
    const problems = validateNodePayload("station", {
      ...station,
      suction_pressure_min_pa: 500000,
      discharge_pressure_max_pa: 200000,
    });

    expect(problems.join(" ")).toContain("refoulement");
  });
});

describe("détails de tronçon", () => {
  const profile = defaultProfile(1000, 10, 25);

  it("accepte un tronçon simple", () => {
    expect(validateEdgeDetails(1000, defaultEdgeGeometry(), 0.5, profile, [])).toEqual([]);
  });

  it("refuse un profil qui ne couvre pas la longueur", () => {
    const problems = validateEdgeDetails(1500, defaultEdgeGeometry(), 0.5, profile, []);

    expect(problems.join(" ")).toContain("longueur du tronçon");
  });

  it("refuse un profil non croissant", () => {
    const reversed = [profile[1], profile[0]];
    const problems = validateEdgeDetails(1000, defaultEdgeGeometry(), 0.5, reversed, []);

    expect(problems.join(" ")).toContain("croissants");
  });

  it("refuse une géométrie incohérente", () => {
    const geometry = { ...defaultEdgeGeometry(), outer_diameter_m: 0.4 };
    const problems = validateEdgeDetails(1000, geometry, 0.5, profile, []);

    expect(problems.join(" ")).toContain("diamètre intérieur");
  });

  it("refuse un accessoire au-delà du tronçon", () => {
    const problems = validateEdgeDetails(1000, defaultEdgeGeometry(), 0.5, profile, [
      { id: "ACC-01", kind: "elbow", k_coefficient: 0.3, quantity: 1, chainage_m: 1500, opening_ratio: 1 },
    ]);

    expect(problems.join(" ")).toContain("au-delà");
  });
});
