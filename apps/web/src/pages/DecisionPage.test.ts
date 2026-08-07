import { describe, expect, it } from "vitest";

import { describeRejection, rejectionConfigurationId } from "./DecisionPage";

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
