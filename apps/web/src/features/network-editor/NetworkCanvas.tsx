import { useMemo } from "react";
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { NetworkEdge, NetworkNode } from "@/types";

interface NetworkCanvasProps {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  interactive?: boolean;
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

export function NetworkCanvas({ nodes, edges, interactive = false }: NetworkCanvasProps) {
  const flowNodes = useMemo<Node[]>(
    () =>
      nodes.map((node, index) => ({
        id: node.id,
        type: node.kind === "source" ? "input" : node.kind === "terminal" ? "output" : "default",
        position: {
          x: 60 + index * 190,
          y: 90 + (index % 2) * 130,
        },
        data: {
          label: `${node.code} — ${node.name}`,
        },
        style: {
          minWidth: 160,
          color: "#ffffff",
          background: NODE_COLORS[node.kind],
          border: "1px solid rgba(255,255,255,.18)",
          borderRadius: 10,
          boxShadow: "0 12px 26px rgba(16,42,51,.16)",
          fontSize: 12,
          fontWeight: 700,
        },
      })),
    [nodes],
  );

  const flowEdges = useMemo<Edge[]>(
    () =>
      edges.map((edge) => ({
        id: edge.id,
        source: edge.from_node_id,
        target: edge.to_node_id,
        label: `${edge.code} · ${(edge.length_m / 1000).toLocaleString("fr-FR", {
          maximumFractionDigits: 2,
        })} km`,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#0F4C5C",
        },
        style: {
          stroke: "#0F4C5C",
          strokeWidth: 2.2,
        },
        labelStyle: {
          fill: "#60747C",
          fontSize: 10,
          fontWeight: 700,
        },
        labelBgStyle: {
          fill: "#F5F7F8",
          fillOpacity: 0.92,
        },
      })),
    [edges],
  );

  return (
    <div className="h-[520px] overflow-hidden rounded-xl border bg-card">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        nodesDraggable={interactive}
        nodesConnectable={interactive}
        elementsSelectable
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
