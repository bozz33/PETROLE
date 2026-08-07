import { describe, expect, it } from "vitest";

import { buildPath } from "./StockagePage";
import type { NetworkEdge } from "../types";

function edge(code: string, from: string, to: string, sequence: number): NetworkEdge {
  return {
    id: code,
    model_version_id: "M",
    from_node_id: from,
    to_node_id: to,
    material_catalog_item_id: null,
    code,
    name: code,
    sequence,
    length_m: 1000,
    inner_diameter_m: 0.5,
    roughness_m: 0.000045,
    mawp_pa: 8_000_000,
    status: "available",
    profile: [],
    fittings: [],
    payload: {},
    created_at: "",
    updated_at: "",
  } as unknown as NetworkEdge;
}

describe("chemin hydraulique", () => {
  const edges = [edge("TR-1", "A", "B", 1), edge("TR-2", "B", "C", 2), edge("TR-3", "C", "D", 3)];

  it("relie deux nœuds par une suite orientée continue", () => {
    expect(buildPath(edges, "A", "C")?.map((item) => item.code)).toEqual(["TR-1", "TR-2"]);
  });

  it("retourne le chemin complet jusqu'au dernier nœud", () => {
    expect(buildPath(edges, "A", "D")?.map((item) => item.code)).toEqual([
      "TR-1",
      "TR-2",
      "TR-3",
    ]);
  });

  it("refuse de deviner une route inexistante", () => {
    expect(buildPath(edges, "D", "A")).toBeNull();
    expect(buildPath(edges, "A", "Z")).toBeNull();
  });

  it("refuse un chemin dégénéré", () => {
    expect(buildPath(edges, "A", "A")).toBeNull();
    expect(buildPath(edges, "", "C")).toBeNull();
  });

  it("ignore une branche morte et retient la branche aboutissant", () => {
    const branched = [...edges, edge("TR-X", "A", "X", 4)];

    expect(buildPath(branched, "A", "D")?.map((item) => item.code)).toEqual([
      "TR-1",
      "TR-2",
      "TR-3",
    ]);
  });
});
