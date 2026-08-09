import { describe, expect, it } from "vitest";

import type { Calculation } from "../types";
import {
  describeRejection,
  rejectionConfigurationId,
  retainExistingCalculationIds,
} from "./DecisionPage";

describe("rejets de l'optimiseur", () => {
  it("restitue les motifs renvoyés par le moteur", () => {
    const entry = { reasons: ["Pression minimale non respectée", "Pompe interdite active"] };

    expect(describeRejection(entry)).toBe(
      "Pression minimale non respectée ; Pompe interdite active",
    );
  });

  it("signale explicitement l'absence de motif au lieu d'afficher un vide", () => {
    expect(describeRejection({ reasons: [] })).toContain("Motif non renseigné");
    expect(describeRejection({})).toContain("Motif non renseigné");
  });

  it("lit l'identifiant dans la configuration rejetée", () => {
    expect(rejectionConfigurationId({ configuration: { id: "P1+P2@1.0" } })).toBe("P1+P2@1.0");
    expect(rejectionConfigurationId({ configuration: {} })).toBe("—");
    expect(rejectionConfigurationId({})).toBe("—");
  });
});

describe("synchronisation des calculs sélectionnés", () => {
  const calculations = [{ id: "calculation-1" }] as Calculation[];

  it("conserve la référence d'état lorsqu'aucune sélection ne doit changer", () => {
    const selected = ["calculation-1"];
    const empty: string[] = [];

    expect(retainExistingCalculationIds(selected, calculations)).toBe(selected);
    expect(retainExistingCalculationIds(empty, calculations)).toBe(empty);
  });

  it("retire seulement les calculs qui ne sont plus disponibles", () => {
    expect(retainExistingCalculationIds(["calculation-1", "obsolete"], calculations)).toEqual([
      "calculation-1",
    ]);
  });
});
