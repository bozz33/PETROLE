import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/api";
import { EmptyState, ErrorNotice, Panel, StatusBadge } from "@/components/Shell";
import { NetworkCanvas } from "@/features/network-editor/NetworkCanvas";
import type {
  ModelVersion,
  NetworkEdge,
  NetworkNode,
  Organization,
  Page,
  Project,
} from "@/types";

export function VisualisationReseauPage() {
  const [organizationId, setOrganizationId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");

  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<Page<Organization>>("/organizations?limit=200&offset=0"),
  });
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

  const organizations = organizationsQuery.data?.items ?? [];
  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];
  const nodes = nodesQuery.data?.items ?? [];
  const edges = edgesQuery.data?.items ?? [];
  const selectedModel = models.find((model) => model.id === modelId);

  useEffect(() => {
    if (!organizationId && organizations.length) {
      setOrganizationId(organizations[0].id);
    }
  }, [organizationId, organizations]);

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

  const error =
    organizationsQuery.error ??
    projectsQuery.error ??
    modelsQuery.error ??
    nodesQuery.error ??
    edgesQuery.error;

  if (error) {
    return <ErrorNotice error={error} />;
  }

  return (
    <div className="stack">
      <Panel
        title="Sélection du modèle"
        description="Choisissez la version à afficher dans le canevas technologique React Flow."
      >
        <div className="form-grid three">
          <label>
            Organisation
            <select
              value={organizationId}
              onChange={(event) => setOrganizationId(event.target.value)}
            >
              <option value="">Sélectionner</option>
              {organizations.map((organization) => (
                <option key={organization.id} value={organization.id}>
                  {organization.name}
                </option>
              ))}
            </select>
          </label>
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
        title="Schéma technologique du réseau"
        description="Les couleurs distinguent les sources, bacs, stations, jonctions, injections et terminaux."
        action={selectedModel ? <StatusBadge value={selectedModel.status} /> : undefined}
      >
        {nodes.length ? (
          <NetworkCanvas nodes={nodes} edges={edges} />
        ) : (
          <EmptyState
            title="Réseau non disponible"
            detail="Sélectionnez un modèle contenant des nœuds et des tronçons structurés."
          />
        )}
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
