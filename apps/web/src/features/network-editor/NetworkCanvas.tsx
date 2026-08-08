import { useCallback, useMemo } from "react";
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { NetworkEdge, NetworkNode, NetworkValidationIssue } from "@/types";

interface NetworkCanvasProps {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  interactive?: boolean;
  /** Anomalies du rapport de validation, signalées directement sur le schéma. */
  issues?: NetworkValidationIssue[];
  selectedId?: string | null;
  onSelect?: (selection: { kind: "node" | "edge"; id: string } | null) => void;
  /** Persiste la position d'un nœud déplacé à la souris. */
  onMoveNode?: (nodeId: string, position: { x: number; y: number }) => void;
}

const NODE_COLORS: Record<NetworkNode["kind"], string> = {
  source: "#2F6FED",
  tank: "#1C7180",
  station: "#0F4C5C",
  junction: "#60747C",
  terminal: "#102A33",
  injection: "#20A39E",
  offtake: "#A96800",
};

const ERROR_COLOR = "#A43A34";
const WARNING_COLOR = "#B8770B";

/**
 * Position d'un nœud sur le schéma.
 *
 * Une position enregistrée dans le modèle est respectée ; sinon le nœud est
 * placé selon son rang dans le chaînage, ce qui donne un tracé lisible d'amont
 * en aval au lieu d'un ordre de création arbitraire.
 */
function layoutPosition(
  node: NetworkNode,
  rank: number,
): { x: number; y: number } {
  const payload = node.payload as { layout?: { x?: unknown; y?: unknown } };
  const stored = payload.layout;
  if (stored && typeof stored.x === "number" && typeof stored.y === "number") {
    return { x: stored.x, y: stored.y };
  }
  return { x: 60 + rank * 210, y: 120 + (rank % 2) * 140 };
}

/** Classe les nœuds d'amont en aval en suivant les tronçons. */
function chainRanks(nodes: NetworkNode[], edges: NetworkEdge[]): Map<string, number> {
  const ordered = [...edges].sort((a, b) => a.sequence - b.sequence);
  const ranks = new Map<string, number>();
  let cursor = 0;
  for (const edge of ordered) {
    if (!ranks.has(edge.from_node_id)) {
      ranks.set(edge.from_node_id, cursor);
      cursor += 1;
    }
    if (!ranks.has(edge.to_node_id)) {
      ranks.set(edge.to_node_id, cursor);
      cursor += 1;
    }
  }
  for (const node of nodes) {
    if (!ranks.has(node.id)) {
      ranks.set(node.id, cursor);
      cursor += 1;
    }
  }
  return ranks;
}

export function NetworkCanvas({
  nodes,
  edges,
  interactive = false,
  issues = [],
  selectedId = null,
  onSelect,
  onMoveNode,
}: NetworkCanvasProps) {
  const severityByObject = useMemo(() => {
    const map = new Map<string, "error" | "warning">();
    for (const issue of issues) {
      const current = map.get(issue.object_id);
      if (issue.severity === "error" || current !== "error") {
        map.set(issue.object_id, issue.severity === "error" ? "error" : "warning");
      }
    }
    return map;
  }, [issues]);

  const ranks = useMemo(() => chainRanks(nodes, edges), [nodes, edges]);

  const flowNodes = useMemo<Node[]>(
    () =>
      nodes.map((node) => {
        const severity = severityByObject.get(node.id);
        const selected = node.id === selectedId;
        return {
          id: node.id,
          type:
            node.kind === "source" ? "input" : node.kind === "terminal" ? "output" : "default",
          position: layoutPosition(node, ranks.get(node.id) ?? 0),
          selected,
          data: { label: `${node.code} — ${node.name}` },
          style: {
            minWidth: 160,
            color: "#ffffff",
            background: NODE_COLORS[node.kind],
            border: severity
              ? `2px solid ${severity === "error" ? ERROR_COLOR : WARNING_COLOR}`
              : selected
                ? "2px solid #F2A516"
                : "1px solid rgba(255,255,255,.18)",
            borderRadius: 10,
            boxShadow: selected
              ? "0 0 0 4px rgba(242,165,22,.25)"
              : "0 12px 26px rgba(16,42,51,.16)",
            fontSize: 12,
            fontWeight: 700,
            opacity: node.status === "available" ? 1 : 0.55,
          },
        };
      }),
    [nodes, ranks, selectedId, severityByObject],
  );

  const flowEdges = useMemo<Edge[]>(
    () =>
      edges.map((edge) => {
        const severity = severityByObject.get(edge.id);
        const selected = edge.id === selectedId;
        const stroke = severity
          ? severity === "error"
            ? ERROR_COLOR
            : WARNING_COLOR
          : selected
            ? "#F2A516"
            : "#0F4C5C";
        return {
          id: edge.id,
          source: edge.from_node_id,
          target: edge.to_node_id,
          label: `${edge.code} · ${(edge.length_m / 1000).toLocaleString("fr-FR", {
            maximumFractionDigits: 2,
          })} km`,
          markerEnd: { type: MarkerType.ArrowClosed, color: stroke },
          style: {
            stroke,
            strokeWidth: selected ? 3.4 : 2.2,
            strokeDasharray: edge.status === "available" ? undefined : "6 4",
          },
          labelStyle: { fill: "#60747C", fontSize: 10, fontWeight: 700 },
          labelBgStyle: { fill: "#F5F7F8", fillOpacity: 0.92 },
        };
      }),
    [edges, selectedId, severityByObject],
  );

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (!onMoveNode) {
        return;
      }
      for (const change of changes) {
        if (change.type === "position" && change.dragging === false && change.position) {
          onMoveNode(change.id, {
            x: Math.round(change.position.x),
            y: Math.round(change.position.y),
          });
        }
      }
    },
    [onMoveNode],
  );

  return (
    <div className="h-[520px] overflow-hidden rounded-xl border bg-card">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        nodesDraggable={interactive}
        nodesConnectable={false}
        elementsSelectable
        onNodesChange={interactive ? handleNodesChange : undefined}
        onNodeClick={(_, node) => onSelect?.({ kind: "node", id: node.id })}
        onEdgeClick={(_, edge) => onSelect?.({ kind: "edge", id: edge.id })}
        onPaneClick={() => onSelect?.(null)}
        minZoom={0.25}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <MiniMap
          pannable
          zoomable
          nodeColor={(node) => String(node.style?.background ?? "#0F4C5C")}
          maskColor="rgba(7,23,28,.08)"
        />
        <Controls showInteractive={interactive} />
        <Background color="#D8E1E4" gap={22} size={1} />
      </ReactFlow>
    </div>
  );
}
