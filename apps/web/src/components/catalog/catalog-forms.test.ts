import { describe, expect, it } from "vitest";

import { defaultFluidPayload, emptyPropertyTable, validateFluid } from "./FluidForm";
import { defaultPumpPayload, validatePump } from "./PumpForm";

describe("fiche produit", () => {
  it("accepte la fiche par défaut", () => {
    expect(validateFluid(defaultFluidPayload())).toEqual([]);
  });

  it("exige une source de masse volumique", () => {
    const payload = { ...defaultFluidPayload(), density_kg_m3: null };

    expect(validateFluid(payload)).toHaveLength(1);
    expect(validateFluid({ ...payload, density_table: emptyPropertyTable() })).toEqual([]);
  });

  it("refuse une table dont les températures ne croissent pas", () => {
    const table = emptyPropertyTable();
    const payload = {
      ...defaultFluidPayload(),
      density_table: {
        ...table,
        points: [table.points[1], table.points[0]],
      },
    };

    expect(validateFluid(payload).join(" ")).toContain("strictement croissantes");
  });
});

describe("fiche pompe", () => {
  it("accepte la fiche par défaut", () => {
    expect(validatePump(defaultPumpPayload())).toEqual([]);
  });

  it("refuse une série optionnelle de longueur différente", () => {
    const payload = defaultPumpPayload();
    payload.curve.efficiencies = [0.7];

    expect(validatePump(payload).join(" ")).toContain("rendement");
  });

  it("refuse des débits non croissants", () => {
    const payload = defaultPumpPayload();
    payload.curve.flows_m3_s = [0.3, 0.2, 0.1];

    expect(validatePump(payload).join(" ")).toContain("strictement croissants");
  });

  it("refuse un rapport de vitesse maximal inférieur au minimal", () => {
    const payload = { ...defaultPumpPayload(), min_speed_ratio: 1.2, max_speed_ratio: 1 };

    expect(validatePump(payload).join(" ")).toContain("rapport de vitesse maximal");
  });
});
