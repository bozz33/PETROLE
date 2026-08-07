import { describe, expect, it } from "vitest";

import {
  defaultAccessoryPayload,
  defaultMaterialPayload,
  defaultValvePayload,
  validateAccessory,
  validateMaterial,
  validateValve,
} from "./EquipmentForms";

describe("fiche vanne", () => {
  it("accepte la fiche par défaut", () => {
    expect(validateValve(defaultValvePayload())).toEqual([]);
  });

  it("exige une grandeur permettant de déterminer la perte", () => {
    const payload = { ...defaultValvePayload(), k_coefficient: null };

    expect(validateValve(payload)).toHaveLength(1);
    expect(validateValve({ ...payload, cv: 1200 })).toEqual([]);
  });
});

describe("fiche matériau", () => {
  it("accepte la fiche par défaut", () => {
    expect(validateMaterial(defaultMaterialPayload())).toEqual([]);
  });

  it("exige la rugosité", () => {
    expect(validateMaterial({ ...defaultMaterialPayload(), roughness_m: null })).toHaveLength(1);
  });

  it("refuse une épaisseur incompatible avec le diamètre extérieur", () => {
    const payload = {
      ...defaultMaterialPayload(),
      outer_diameter_m: 0.3,
      wall_thickness_m: 0.2,
    };

    expect(validateMaterial(payload).join(" ")).toContain("incompatible");
  });
});

describe("fiche accessoire", () => {
  it("accepte la fiche par défaut", () => {
    expect(validateAccessory(defaultAccessoryPayload())).toEqual([]);
  });

  it("exige un K ou une longueur équivalente", () => {
    const payload = { ...defaultAccessoryPayload(), k_coefficient: null };

    expect(validateAccessory(payload)).toHaveLength(1);
    expect(validateAccessory({ ...payload, equivalent_length_m: 12 })).toEqual([]);
  });
});
