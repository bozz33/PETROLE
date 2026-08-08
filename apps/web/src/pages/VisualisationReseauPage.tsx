import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { OrganizationField } from "../components/OrganizationField";
import { apiRequest, jsonBody } from "@/api";
import { PipelineMap } from "@/components/maps/PipelineMap";
import { EmptyState, ErrorNotice, Panel, StatusBadge } from "@/components/Shell";
import {
  ElementInspector,
  type EdgePatch,
  type NodePatch,
} from "@/features/network-editor/ElementInspector";
import { NetworkCanvas } from "@/features/network-editor/NetworkCanvas";
import type {
  ModelVersion,
  NetworkEdge,
  NetworkNode,
  AssetInstance,
  NetworkValidationReport,
  Page,
  Project,
} from "@/types";

type ViewMode = "schema" | "map";

export function VisualisationReseauPage() {
  const [organizationId, setOrganizationId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("schema");
  const [selection, setSelection] = useState<{
    kind: "node" | "edge" | "asset";
    id: string;
  } | null>(null);
  const queryClient = useQueryClient();

  const projectsQuery = useQuery({
    queryKey: ["projects", organizationId],
    queryFn: () =>
      apiRequest<Page<Project>>(
        `/projects?limit=200&offset=0&organization_id=${organizationId}`,
      ),
    enabled: Boolean(organizationId),
  });
  const modelsQuery = useQuery({
    queryKey: ["models", projectId],
    queryFn: () =>
      apiRequest<Page<ModelVersion>>(`/projects/${projectId}/models?limit=200&offset=0`),
    enabled: Boolean(projectId),
  });
  const nodesQuery = useQuery({
    queryKey: ["network-nodes", modelId],
    queryFn: () =>
      apiRequest<Page<NetworkNode>>(`/models/${modelId}/nodes?limit=1000&offset=0`),
    enabled: Boolean(modelId),
  });
  const edgesQuery = useQuery({
    queryKey: ["network-edges", modelId],
    queryFn: () =>
      apiRequest<Page<NetworkEdge>>(`/models/${modelId}/edges?limit=2000&offset=0`),
    enabled: Boolean(modelId),
  });

  const assetsQuery = useQuery({
    queryKey: ["network-assets", modelId],
    queryFn: () =>
      apiRequest<Page<AssetInstance>>(`/models/${modelId}/assets?limit=2000&offset=0`),
    enabled: Boolean(modelId),
  });

  const validationQuery = useQuery({
    queryKey: ["network-validation", modelId],
    queryFn: () =>
      apiRequest<NetworkValidationReport>(`/models/${modelId}/validate`, { method: "POST" }),
    enabled: Boolean(modelId),
  });

  const invalidateNetwork = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["network-nodes", modelId] }),
      queryClient.invalidateQueries({ queryKey: ["network-edges", modelId] }),
      queryClient.invalidateQueries({ queryKey: ["network-validation", modelId] }),
    ]);
  };

  const nodePatchMutation = useMutation({
    mutationFn: ({ nodeId, patch }: { nodeId: string; patch: NodePatch }) =>
      apiRequest<NetworkNode>(`/nodes/${nodeId}`, {
        method: "PATCH",
        body: jsonBody(patch),
      }),
    onSuccess: invalidateNetwork,
  });

  const edgePatchMutation = useMutation({
    mutationFn: ({ edgeId, patch }: { edgeId: string; patch: EdgePatch }) =>
      apiRequest<NetworkEdge>(`/edges/${edgeId}`, {
        method: "PATCH",
        body: jsonBody(patch),
      }),
    onSuccess: invalidateNetwork,
  });

  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];
  const nodes = nodesQuery.data?.items ?? [];
  const edges = edgesQuery.data?.items ?? [];
  const assets = assetsQuery.data?.items ?? [];
  const selectedModel = models.find((model) => model.id === modelId);
  const mapPoints = nodes
    .filter(
      (node): node is NetworkNode & { latitude: number; longitude: number } =>
        node.latitude !== null && node.longitude !== null,
    )
    .map((node) => ({ latitude: node.latitude, longitude: node.longitude }));
  const mapStyleUrl =
    import.meta.env.VITE_MAP_STYLE_URL ?? "https://demotiles.maplibre.org/style.json";


  useEffect(() => {
    if (!projects.some((project) => project.id === projectId)) {
      setProjectId(projects[0]?.id ?? "");
    }
  }, [projectId, projects]);

  useEffect(() => {
    if (!models.some((model) => model.id === modelId)) {
      setModelId(
        models.find((model) => model.status === "approved")?.id ?? models[0]?.id ?? "",
      );
    }
  }, [modelId, models]);

  const editable = selectedModel?.status === "draft";
  const validationErrors = validationQuery.data?.errors ?? [];
  const validationWarnings = validationQuery.data?.warnings ?? [];
  const issues = [...validationErrors, ...validationWarnings];
  const selectedNode =
    selection?.kind === "node" ? (nodes.find((item) => item.id === selection.id) ?? null) : null;
  const selectedEdge =
    selection?.kind === "edge" ? (edges.find((item) => item.id === selection.id) ?? null) : null;
  const selectedAsset =
    selection?.kind === "asset" ? (assets.find((item) => item.id === selection.id) ?? null) : null;

  const error =
    projectsQuery.error ??
    modelsQuery.error ??
    nodesQuery.error ??
    edgesQuery.error ??
    assetsQuery.error ??
    nodePatchMutation.error ??
    edgePatchMutation.error;

  if (error) {
    return <ErrorNotice error={error} />;
  }

  return (
    <div className="stack">
      <Panel
        title="Sélection du modèle"
        description="Choisissez la version à afficher dans le schéma technologique ou sur la carte."
      >
        <div className="form-grid three">
          <OrganizationField value={organizationId} onChange={setOrganizationId} />
          <label>
            Projet
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
              <option value="">Sélectionner</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.code} — {project.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Version
            <select value={modelId} onChange={(event) => setModelId(event.target.value)}>
              <option value="">Sélectionner</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  V{model.version_number} — {model.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>

      <Panel
        title={viewMode === "schema" ? "Schéma technologique du réseau" : "Carte du réseau"}
        description={
          viewMode === "schema"
            ? "Les couleurs distinguent les sources, bacs, stations, jonctions, injections et terminaux."
            : "La carte utilise les coordonnées géographiques renseignées sur les nœuds du modèle."
        }
        action={
          <div className="inline-actions">
            {selectedModel ? <StatusBadge value={selectedModel.status} /> : null}
            <button
              className={viewMode === "schema" ? "button button-primary" : "button button-secondary"}
              type="button"
              aria-pressed={viewMode === "schema"}
              onClick={() => setViewMode("schema")}
            >
              Schéma
            </button>
            <button
              className={viewMode === "map" ? "button button-primary" : "button button-secondary"}
              type="button"
              aria-pressed={viewMode === "map"}
              onClick={() => setViewMode("map")}
            >
              Carte
            </button>
          </div>
        }
      >
        {viewMode === "schema" ? (
          nodes.length ? (
            <NetworkCanvas
              nodes={nodes}
              edges={edges}
              assets={assets}
              interactive={editable}
              errors={validationErrors}
              warnings={validationWarnings}
              selectedId={selection?.id ?? null}
              onSelect={setSelection}
              onMoveNode={(nodeId, position) =>
                nodePatchMutation.mutate({
                  nodeId,
                  patch: {
                    payload: {
                      ...((nodes.find((item) => item.id === nodeId)?.payload ?? {}) as Record<
                        string,
                        unknown
                      >),
                      layout: position,
                    },
                  } as NodePatch,
                })
              }
            />
          ) : (
            <EmptyState
              title="Réseau non disponible"
              detail="Sélectionnez un modèle contenant des nœuds et des tronçons structurés."
            />
          )
        ) : mapPoints.length >= 2 ? (
          <PipelineMap points={mapPoints} styleUrl={mapStyleUrl} />
        ) : (
          <EmptyState
            title="Coordonnées insuffisantes"
            detail="Renseignez la latitude et la longitude d'au moins deux nœuds pour tracer le pipeline."
          />
        )}
      </Panel>

      {issues.length ? (
        <Panel
          title="Anomalies du réseau"
          description="Cliquez une anomalie pour sélectionner l'objet concerné sur le schéma."
        >
          <ul className="issue-list negative">
            {issues.map((issue) => (
              <li key={`${issue.code}-${issue.object_id ?? "modele"}-${issue.message}`}>
                <strong>{issue.code}</strong>
                <span>
                  {issue.object_id ? (
                    <button
                      type="button"
                      className="button button-ghost"
                      onClick={() => {
                        const objectId = issue.object_id;
                        if (!objectId) {
                          return;
                        }
                        if (nodes.some((item) => item.id === objectId)) {
                          setSelection({ kind: "node", id: objectId });
                        } else if (edges.some((item) => item.id === objectId)) {
                          setSelection({ kind: "edge", id: objectId });
                        } else if (assets.some((item) => item.id === objectId)) {
                          setSelection({ kind: "asset", id: objectId });
                        }
                        setViewMode("schema");
                      }}
                    >
                      {issue.message}
                    </button>
                  ) : (
                    issue.message
                  )}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}

      <Panel
        title="Propriétés de l'élément"
        description="Sélectionnez un nœud ou un tronçon du schéma pour l'inspecter et l'ajuster."
      >
        <ElementInspector
          node={selectedNode}
          edge={selectedEdge}
          asset={selectedAsset}
          nodes={nodes}
          issues={issues}
          editable={editable}
          pending={nodePatchMutation.isPending || edgePatchMutation.isPending}
          onPatchNode={(nodeId, patch) => nodePatchMutation.mutate({ nodeId, patch })}
          onPatchEdge={(edgeId, patch) => edgePatchMutation.mutate({ edgeId, patch })}
        />
      </Panel>

      <div className="resource-summary">
        <div>
          <span>Nœuds</span>
          <strong>{nodes.length}</strong>
        </div>
        <div>
          <span>Tronçons</span>
          <strong>{edges.length}</strong>
        </div>
        <div>
          <span>Équipements placés</span>
          <strong>{assets.length}</strong>
        </div>
        <div>
          <span>Nœuds géolocalisés</span>
          <strong>{mapPoints.length}</strong>
        </div>
        <div>
          <span>Anomalies détectées</span>
          <strong>
            {validationQuery.data
              ? `${validationErrors.length} erreur(s) · ${validationWarnings.length} avertissement(s)`
              : "—"}
          </strong>
        </div>
        <div>
          <span>Longueur cumulée</span>
          <strong>
            {(edges.reduce((total, edge) => total + edge.length_m, 0) / 1000).toLocaleString(
              "fr-FR",
              { maximumFractionDigits: 2 },
            )}{" "}
            km
          </strong>
        </div>
      </div>
    </div>
  );
}
