import { describe, expect, it } from "vitest";

import { chainRanks, layoutPosition, severityMap } from "./NetworkCanvas";
import type { NetworkEdge, NetworkNode } from "@/types";

function node(id: string, overrides: Partial<NetworkNode> = {}): NetworkNode {
  return {
    id,
    model_version_id: "M",
    code: id,
    name: id,
    kind: "junction",
    elevation_m: 0,
    latitude: null,
    longitude: null,
    status: "available",
    payload: {},
    created_at: "",
    updated_at: "",
    ...overrides,
  } as NetworkNode;
}

function edge(id: string, from: string, to: string, sequence: number): NetworkEdge {
  return { id, from_node_id: from, to_node_id: to, sequence } as NetworkEdge;
}

describe("disposition du schéma", () => {
  it("classe les nœuds d'amont en aval selon le chaînage", () => {
    const nodes = [node("C"), node("A"), node("B")];
    const edges = [edge("E1", "A", "B", 1), edge("E2", "B", "C", 2)];

    const ranks = chainRanks(nodes, edges);

    expect(ranks.get("A")).toBeLessThan(ranks.get("B")!);
    expect(ranks.get("B")).toBeLessThan(ranks.get("C")!);
  });

  it("place les nœuds isolés après ceux du chaînage", () => {
    const ranks = chainRanks([node("A"), node("B"), node("Z")], [edge("E1", "A", "B", 1)]);

    expect(ranks.get("Z")).toBeGreaterThan(ranks.get("B")!);
  });

  it("respecte une position enregistrée dans le modèle", () => {
    const placed = node("A", { payload: { layout: { x: 400, y: 250 } } });

    expect(layoutPosition(placed, 0)).toEqual({ x: 400, y: 250 });
  });

  it("ignore une position incomplète et retombe sur le rang", () => {
    const broken = node("A", { payload: { layout: { x: 400 } } });

    expect(layoutPosition(broken, 2)).toEqual({ x: 480, y: 120 });
  });
});

describe("signalement des anomalies", () => {
  const issue = (objectId: string) => ({
    code: "NET_X",
    message: "anomalie",
    object_type: "node",
    object_id: objectId,
  });

  it("retient l'erreur lorsqu'un objet porte aussi un avertissement", () => {
    const map = severityMap([issue("A")], [issue("A")]);

    expect(map.get("A")).toBe("error");
  });

  it("ignore une anomalie sans objet rattaché", () => {
    const map = severityMap([], [{ ...issue("A"), object_id: null }]);

    expect(map.size).toBe(0);
  });
});
