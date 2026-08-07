import { describe, expect, it } from "vitest";

import { defaultTankDraft, theoreticalStrapping, validateTank } from "./TankForm";

describe("fiche de bac", () => {
  it("accepte la fiche par défaut", () => {
    expect(validateTank({ ...defaultTankDraft(), name: "Bac 1", code: "T1" })).toEqual([]);
  });

  it("exige un nom et un code", () => {
    expect(validateTank(defaultTankDraft()).join(" ")).toContain("obligatoires");
  });

  it("refuse un barémage non croissant", () => {
    const draft = { ...defaultTankDraft(), name: "Bac", code: "T1" };
    draft.strapping = [
      { height_m: 5, volume_m3: 100 },
      { height_m: 2, volume_m3: 50 },
    ];

    expect(validateTank(draft).join(" ")).toContain("strictement croissant");
  });

  it("refuse un niveau courant au-dessus de la hauteur barémée", () => {
    const draft = { ...defaultTankDraft(), name: "Bac", code: "T1", current_level_m: 99 };

    expect(validateTank(draft).join(" ")).toContain("dépasse la hauteur barémée");
  });

  it("refuse des seuils désordonnés", () => {
    const draft = { ...defaultTankDraft(), name: "Bac", code: "T1" };
    draft.levels = { ...draft.levels, minimum_m: 10, low_m: 1 };

    expect(validateTank(draft).join(" ")).toContain("ordonnés");
  });

  it("produit un barémage linéaire à deux points", () => {
    expect(theoreticalStrapping(12, 10000)).toEqual([
      { height_m: 0, volume_m3: 0 },
      { height_m: 12, volume_m3: 10000 },
    ]);
  });
});
