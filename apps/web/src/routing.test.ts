import { describe, expect, it } from "vitest";

import { validatedPath } from "./routing";

describe("validatedPath", () => {
  it("conserve la racine et normalise la barre finale", () => {
    expect(validatedPath("/")).toBe("/");
    expect(validatedPath("/projets/")).toBe("/projets");
  });

  it("accepte uniquement les chemins locaux prévisibles", () => {
    expect(validatedPath("/calcul/resultats_1")).toBe("/calcul/resultats_1");
    expect(() => validatedPath("https://example.test")).toThrow();
    expect(() => validatedPath("//example.test")).toThrow();
    expect(() => validatedPath("/projets?organisation=1")).toThrow();
    expect(() => validatedPath("/../administration")).toThrow();
  });
});
