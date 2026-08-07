import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { OrganizationField } from "../components/OrganizationField";
import {
  defaultEdgeGeometry,
  defaultProfile,
  EdgeDetailsForm,
  validateEdgeDetails,
} from "../components/network/EdgeDetailsForm";
import {
  defaultNodePayload,
  NodePayloadForm,
  validateNodePayload,
} from "../components/network/NodePayloadForm";
import { apiRequest, jsonBody } from "../api";
import {
  EmptyState,
  ErrorNotice,
  Panel,
  StatusBadge,
  SuccessNotice,
} from "../components/Shell";
import type {
  AssetInstance,
  CatalogCollection,
  CatalogItem,
  ModelVersion,
  NetworkEdge,
  NetworkNode,
  NetworkValidationReport,
  NodePayload,
  Page,
  ProfilePoint,
  EdgeFitting,
  EdgeGeometry,
  Project,
} from "../types";

const EQUIPMENT_COLLECTIONS: CatalogCollection[] = [
  "pumps",
  "valves",
  "accessories",
  "materials",
];

export function ModelisationPage() {
  const queryClient = useQueryClient();
  const [organizationId, setOrganizationId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");

  const [nodeCode, setNodeCode] = useState("");
  const [nodeName, setNodeName] = useState("");
  const [nodeKind, setNodeKind] = useState<NetworkNode["kind"]>("source");
  const [nodeElevation, setNodeElevation] = useState("0");
  const [nodeLatitude, setNodeLatitude] = useState("");
  const [nodeLongitude, setNodeLongitude] = useState("");
  const [nodeStatus, setNodeStatus] = useState<NetworkNode["status"]>("available");
  const [nodePayload, setNodePayload] = useState<NodePayload>(() => defaultNodePayload("source"));

  const [edgeCode, setEdgeCode] = useState("");
  const [edgeName, setEdgeName] = useState("");
  const [edgeFromId, setEdgeFromId] = useState("");
  const [edgeToId, setEdgeToId] = useState("");
  const [edgeSequence, setEdgeSequence] = useState("1");
  const [edgeLength, setEdgeLength] = useState("1000");
  const [edgeDiameter, setEdgeDiameter] = useState("0.5");
  const [edgeRoughness, setEdgeRoughness] = useState("0.000045");
  const [edgeMawp, setEdgeMawp] = useState("8000000");
  const [edgeMaterialId, setEdgeMaterialId] = useState("");
  const [edgeStatus, setEdgeStatus] = useState<NetworkEdge["status"]>("available");
  const [edgeGeometry, setEdgeGeometry] = useState<EdgeGeometry>(defaultEdgeGeometry);
  const [edgeProfile, setEdgeProfile] = useState<ProfilePoint[]>(() => defaultProfile(1000, 0, 0));
  const [edgeFittings, setEdgeFittings] = useState<EdgeFitting[]>([]);

  const [assetCatalogId, setAssetCatalogId] = useState("");
  const [assetLocationType, setAssetLocationType] = useState<"node" | "edge">("node");
  const [assetLocationId, setAssetLocationId] = useState("");
  const [assetCode, setAssetCode] = useState("");
  const [assetName, setAssetName] = useState("");
  const [assetRole, setAssetRole] = useState<AssetInstance["role"]>("main");
  const [assetPayload, setAssetPayload] = useState("{}");

  const projectsQuery = useQuery({
    queryKey: ["projects", organizationId],
    queryFn: () =>
      apiRequest<Page<Project>>(
        "/projects?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });
  const modelsQuery = useQuery({
    queryKey: ["models", projectId],
    queryFn: () =>
      apiRequest<Page<ModelVersion>>(
        "/projects/" + projectId + "/models?limit=200&offset=0",
      ),
    enabled: Boolean(projectId),
  });
  const nodesQuery = useQuery({
    queryKey: ["network-nodes", modelId],
    queryFn: () =>
      apiRequest<Page<NetworkNode>>(
        "/models/" + modelId + "/nodes?limit=1000&offset=0",
      ),
    enabled: Boolean(modelId),
  });
  const edgesQuery = useQuery({
    queryKey: ["network-edges", modelId],
    queryFn: () =>
      apiRequest<Page<NetworkEdge>>(
        "/models/" + modelId + "/edges?limit=2000&offset=0",
      ),
    enabled: Boolean(modelId),
  });
  const assetsQuery = useQuery({
    queryKey: ["network-assets", modelId],
    queryFn: () =>
      apiRequest<Page<AssetInstance>>(
        "/models/" + modelId + "/assets?limit=2000&offset=0",
      ),
    enabled: Boolean(modelId),
  });
  const equipmentQuery = useQuery({
    queryKey: ["approved-equipment", organizationId],
    queryFn: async () => {
      const pages = await Promise.all(
        EQUIPMENT_COLLECTIONS.map((collection) =>
          apiRequest<Page<CatalogItem>>(
            "/catalog/" +
              collection +
              "?status=approved&limit=500&offset=0&organization_id=" +
              organizationId,
          ),
        ),
      );
      return pages.flatMap((page) => page.items);
    },
    enabled: Boolean(organizationId),
  });

  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];
  const nodes = nodesQuery.data?.items ?? [];
  const edges = edgesQuery.data?.items ?? [];
  const assets = assetsQuery.data?.items ?? [];
  const equipment = equipmentQuery.data ?? [];
  const materials = equipment.filter((item) => item.kind === "material");
  const placeableEquipment = equipment.filter((item) => item.kind !== "material");
  const selectedModel = useMemo(
    () => models.find((model) => model.id === modelId),
    [modelId, models],
  );
  const nodeNames = useMemo(
    () => new Map(nodes.map((node) => [node.id, node.code + " — " + node.name])),
    [nodes],
  );
  const edgeNames = useMemo(
    () => new Map(edges.map((edge) => [edge.id, edge.code + " — " + edge.name])),
    [edges],
  );
  const catalogNames = useMemo(
    () => new Map(equipment.map((item) => [item.id, item.code + " — " + item.name])),
    [equipment],
  );


  useEffect(() => {
    if (!projectId || !projects.some((project) => project.id === projectId)) {
      setProjectId(projects[0]?.id ?? "");
    }
  }, [projectId, projects]);

  useEffect(() => {
    if (!modelId || !models.some((model) => model.id === modelId)) {
      setModelId(models.find((model) => model.status === "draft")?.id ?? models[0]?.id ?? "");
    }
  }, [modelId, models]);

  useEffect(() => {
    if (!edgeFromId || !nodes.some((node) => node.id === edgeFromId)) {
      setEdgeFromId(nodes[0]?.id ?? "");
    }
    if (!edgeToId || !nodes.some((node) => node.id === edgeToId)) {
      setEdgeToId(nodes[1]?.id ?? "");
    }
    if (assetLocationType === "node" && !nodes.some((node) => node.id === assetLocationId)) {
      setAssetLocationId(nodes[0]?.id ?? "");
    }
  }, [assetLocationId, assetLocationType, edgeFromId, edgeToId, nodes]);

  useEffect(() => {
    if (assetLocationType === "edge" && !edges.some((edge) => edge.id === assetLocationId)) {
      setAssetLocationId(edges[0]?.id ?? "");
    }
    setEdgeSequence(String(edges.length + 1));
  }, [assetLocationId, assetLocationType, edges]);

  useEffect(() => {
    if (!assetCatalogId || !placeableEquipment.some((item) => item.id === assetCatalogId)) {
      setAssetCatalogId(placeableEquipment[0]?.id ?? "");
    }
  }, [assetCatalogId, placeableEquipment]);

  const invalidateNetwork = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["network-nodes", modelId] }),
      queryClient.invalidateQueries({ queryKey: ["network-edges", modelId] }),
      queryClient.invalidateQueries({ queryKey: ["network-assets", modelId] }),
    ]);
  };

  useEffect(() => {
    if (edgeProfile.length > 2) {
      return;
    }
    const length = Number(edgeLength);
    if (!Number.isFinite(length) || length <= 0) {
      return;
    }
    const fromElevation = nodes.find((node) => node.id === edgeFromId)?.elevation_m ?? 0;
    const toElevation = nodes.find((node) => node.id === edgeToId)?.elevation_m ?? 0;
    setEdgeProfile((current) =>
      current.length > 2 ? current : defaultProfile(length, fromElevation, toElevation),
    );
  }, [edgeFromId, edgeLength, edgeProfile.length, edgeToId, nodes]);

  const nodePayloadProblems = validateNodePayload(nodeKind, nodePayload);
  const edgeProblems = validateEdgeDetails(
    Number(edgeLength),
    edgeGeometry,
    Number(edgeDiameter),
    edgeProfile,
    edgeFittings,
  );

  const nodeMutation = useMutation({
    mutationFn: () =>
      apiRequest<NetworkNode>("/models/" + modelId + "/nodes", {
        method: "POST",
        body: jsonBody({
          code: nodeCode,
          name: nodeName,
          kind: nodeKind,
          elevation_m: Number(nodeElevation),
          latitude: optionalCoordinate(nodeLatitude),
          longitude: optionalCoordinate(nodeLongitude),
          status: nodeStatus,
          payload: nodePayload as unknown as Record<string, unknown>,
        }),
      }),
    onSuccess: async () => {
      setNodeCode("");
      setNodeName("");
      setNodeLatitude("");
      setNodeLongitude("");
      setNodePayload(defaultNodePayload(nodeKind));
      await invalidateNetwork();
    },
  });

  const edgeMutation = useMutation({
    mutationFn: () => {
      const length = Number(edgeLength);
      return apiRequest<NetworkEdge>("/models/" + modelId + "/edges", {
        method: "POST",
        body: jsonBody({
          from_node_id: edgeFromId,
          to_node_id: edgeToId,
          material_catalog_item_id: edgeMaterialId || null,
          code: edgeCode,
          name: edgeName,
          sequence: Number(edgeSequence),
          length_m: length,
          inner_diameter_m: Number(edgeDiameter),
          roughness_m: Number(edgeRoughness),
          mawp_pa: Number(edgeMawp),
          status: edgeStatus,
          profile: edgeProfile,
          fittings: edgeFittings as unknown as Array<Record<string, unknown>>,
          payload: edgeGeometry as unknown as Record<string, unknown>,
        }),
      });
    },
    onSuccess: async () => {
      setEdgeCode("");
      setEdgeName("");
      setEdgeFittings([]);
      setEdgeGeometry(defaultEdgeGeometry());
      await invalidateNetwork();
    },
  });

  const assetMutation = useMutation({
    mutationFn: () =>
      apiRequest<AssetInstance>("/models/" + modelId + "/assets", {
        method: "POST",
        body: jsonBody({
          catalog_item_id: assetCatalogId,
          node_id: assetLocationType === "node" ? assetLocationId : null,
          edge_id: assetLocationType === "edge" ? assetLocationId : null,
          code: assetCode,
          name: assetName,
          role: assetRole,
          payload: JSON.parse(assetPayload) as Record<string, unknown>,
        }),
      }),
    onSuccess: async () => {
      setAssetCode("");
      setAssetName("");
      setAssetPayload("{}");
      await invalidateNetwork();
    },
  });

  const validationMutation = useMutation({
    mutationFn: () =>
      apiRequest<NetworkValidationReport>("/models/" + modelId + "/validate", {
        method: "POST",
      }),
  });

  const canonicalMutation = useMutation({
    mutationFn: () =>
      apiRequest<Record<string, unknown>>(
        "/models/" + modelId + "/canonical-sections",
      ),
  });

  const error =
    projectsQuery.error ??
    modelsQuery.error ??
    nodesQuery.error ??
    edgesQuery.error ??
    assetsQuery.error ??
    equipmentQuery.error ??
    nodeMutation.error ??
    edgeMutation.error ??
    assetMutation.error ??
    validationMutation.error ??
    canonicalMutation.error;
  const success = nodeMutation.isSuccess || edgeMutation.isSuccess || assetMutation.isSuccess;
  const editable = selectedModel?.status === "draft";
  const validation = validationMutation.data;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {success ? <SuccessNotice>Le modèle structuré a été mis à jour et audité.</SuccessNotice> : null}

      <Panel
        title="Contexte de modélisation"
        description="L'édition structurée reste attachée à une version précise et immuable après approbation."
      >
        <div className="form-grid three">
          <OrganizationField value={organizationId} onChange={setOrganizationId} />
          <label>
            Projet
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
              <option value="">Sélectionner</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.code} — {project.name}</option>
              ))}
            </select>
          </label>
          <label>
            Version du modèle
            <select value={modelId} onChange={(event) => setModelId(event.target.value)}>
              <option value="">Sélectionner</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>V{model.version_number} — {model.name} — {model.status}</option>
              ))}
            </select>
          </label>
        </div>
        {selectedModel ? (
          <div className="resource-summary">
            <div><span>Statut</span><strong>{selectedModel.status}</strong></div>
            <div><span>Nœuds</span><strong>{nodes.length}</strong></div>
            <div><span>Tronçons</span><strong>{edges.length}</strong></div>
            <div><span>Équipements</span><strong>{assets.length}</strong></div>
          </div>
        ) : null}
      </Panel>

      <Panel
        title="Validation topologique"
        description="Contrôle la continuité, les références approuvées et la capacité d'assemblage."
        action={
          <div className="inline-actions">
            <button
              className="button button-primary"
              onClick={() => validationMutation.mutate()}
              disabled={!modelId || validationMutation.isPending}
            >
              Valider le modèle
            </button>
            <button
              className="button button-secondary"
              onClick={() => canonicalMutation.mutate()}
              disabled={!modelId || canonicalMutation.isPending}
            >
              Prévisualiser l'entrée
            </button>
          </div>
        }
      >
        {validation ? (
          <div className="validation-report">
            <StatusBadge value={validation.valid ? "valide" : "invalide"} />
            <p>{validation.errors.length} erreur(s), {validation.warnings.length} avertissement(s).</p>
            {[...validation.errors, ...validation.warnings].map((issue, index) => (
              <div className="validation-line" key={issue.code + index}>
                <strong>{issue.code}</strong><span>{issue.message}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="field-help">Lancez le contrôle avant d'approuver la version.</p>
        )}
        {canonicalMutation.data ? (
          <details className="editor-details">
            <summary>Sections canoniques assemblées</summary>
            <pre className="json-preview">{JSON.stringify(canonicalMutation.data, null, 2)}</pre>
          </details>
        ) : null}
      </Panel>

      <Panel title="Nœuds" description="Sources, stations, jonctions, injections, soutirages et terminaux.">
        {nodes.length ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Code</th><th>Type</th><th>Altitude</th><th>Statut</th></tr></thead>
              <tbody>
                {nodes.map((node, index) => (
                  <tr key={node.id}>
                    <td>{index + 1}</td><td><strong>{node.code}</strong><small>{node.name}</small></td>
                    <td>{node.kind}</td><td>{node.elevation_m} m</td><td><StatusBadge value={node.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState title="Aucun nœud" detail="Ajoutez au minimum une source et un terminal." />}
        <details open={!nodes.length && editable}>
          <summary>Ajouter un nœud</summary>
          <form className="compact-form" onSubmit={(event) => { event.preventDefault(); nodeMutation.mutate(); }}>
            <div className="form-grid three">
              <label>Code<input value={nodeCode} onChange={(event) => setNodeCode(event.target.value.toUpperCase())} required /></label>
              <label>Nom<input value={nodeName} onChange={(event) => setNodeName(event.target.value)} required /></label>
              <label>Type<select value={nodeKind} onChange={(event) => {
                const nextKind = event.target.value as NetworkNode["kind"];
                setNodeKind(nextKind);
                setNodePayload(defaultNodePayload(nextKind));
              }}>
                <option value="source">Source</option><option value="tank">Réservoir</option>
                <option value="station">Station</option><option value="junction">Jonction</option>
                <option value="injection">Injection</option><option value="offtake">Soutirage</option>
                <option value="terminal">Terminal</option>
              </select></label>
            </div>
            <div className="form-grid three">
              <label>Altitude (m)<input type="number" step="any" value={nodeElevation} onChange={(event) => setNodeElevation(event.target.value)} required /></label>
              <label>Latitude<input type="number" step="any" min="-90" max="90" value={nodeLatitude} onChange={(event) => setNodeLatitude(event.target.value)} placeholder="Facultative" /></label>
              <label>Longitude<input type="number" step="any" min="-180" max="180" value={nodeLongitude} onChange={(event) => setNodeLongitude(event.target.value)} placeholder="Facultative" /></label>
            </div>
            <label>État<select value={nodeStatus} onChange={(event) => setNodeStatus(event.target.value as NetworkNode["status"])}>
              <option value="available">Disponible</option>
              <option value="maintenance">En maintenance</option>
              <option value="unavailable">Indisponible</option>
            </select></label>
            <NodePayloadForm kind={nodeKind} value={nodePayload} onChange={setNodePayload} />
            {nodePayloadProblems.length ? (
              <div className="notice notice-error" role="alert">
                <ul className="issue-list negative">
                  {nodePayloadProblems.map((problem) => (
                    <li key={problem}><span>{problem}</span></li>
                  ))}
                </ul>
              </div>
            ) : null}
            <button className="button button-primary" disabled={!editable || nodeMutation.isPending || nodePayloadProblems.length > 0}>Ajouter le nœud</button>
          </form>
        </details>
      </Panel>

      <Panel title="Tronçons" description="Conduites orientées, profil local, matériau et limites de pression.">
        {edges.length ? (
          <div className="table-wrap"><table><thead><tr><th>Séquence</th><th>Tronçon</th><th>Connexion</th><th>Longueur</th><th>Diamètre</th><th>MAWP</th></tr></thead>
            <tbody>{edges.map((edge) => <tr key={edge.id}><td>{edge.sequence}</td><td><strong>{edge.code}</strong><small>{edge.name}</small></td><td>{nodeNames.get(edge.from_node_id)} → {nodeNames.get(edge.to_node_id)}</td><td>{edge.length_m} m</td><td>{edge.inner_diameter_m} m</td><td>{edge.mawp_pa} Pa</td></tr>)}</tbody>
          </table></div>
        ) : <EmptyState title="Aucun tronçon" detail="Reliez deux nœuds avec une conduite dimensionnée." />}
        <details open={Boolean(nodes.length >= 2 && !edges.length && editable)}>
          <summary>Ajouter un tronçon</summary>
          <form className="compact-form" onSubmit={(event) => { event.preventDefault(); edgeMutation.mutate(); }}>
            <div className="form-grid three">
              <label>Code<input value={edgeCode} onChange={(event) => setEdgeCode(event.target.value.toUpperCase())} required /></label>
              <label>Nom<input value={edgeName} onChange={(event) => setEdgeName(event.target.value)} required /></label>
              <label>Séquence<input type="number" min="1" value={edgeSequence} onChange={(event) => setEdgeSequence(event.target.value)} required /></label>
            </div>
            <div className="form-grid">
              <label>Depuis<select value={edgeFromId} onChange={(event) => setEdgeFromId(event.target.value)}><option value="">Sélectionner</option>{nodes.map((node) => <option key={node.id} value={node.id}>{node.code} — {node.name}</option>)}</select></label>
              <label>Vers<select value={edgeToId} onChange={(event) => setEdgeToId(event.target.value)}><option value="">Sélectionner</option>{nodes.map((node) => <option key={node.id} value={node.id}>{node.code} — {node.name}</option>)}</select></label>
            </div>
            <div className="form-grid three">
              <label>Longueur (m)<input type="number" min="0" step="any" value={edgeLength} onChange={(event) => setEdgeLength(event.target.value)} required /></label>
              <label>Diamètre intérieur (m)<input type="number" min="0" step="any" value={edgeDiameter} onChange={(event) => setEdgeDiameter(event.target.value)} required /></label>
              <label>Rugosité (m)<input type="number" min="0" step="any" value={edgeRoughness} onChange={(event) => setEdgeRoughness(event.target.value)} required /></label>
            </div>
            <div className="form-grid">
              <label>MAWP (Pa)<input type="number" min="0" step="any" value={edgeMawp} onChange={(event) => setEdgeMawp(event.target.value)} required /></label>
              <label>Matériau approuvé<select value={edgeMaterialId} onChange={(event) => setEdgeMaterialId(event.target.value)}><option value="">Aucun matériau lié</option>{materials.map((item) => <option key={item.id} value={item.id}>{item.code} — {item.name}</option>)}</select></label>
            </div>
            <label>État<select value={edgeStatus} onChange={(event) => setEdgeStatus(event.target.value as NetworkEdge["status"])}>
              <option value="available">Disponible</option>
              <option value="maintenance">En maintenance</option>
              <option value="unavailable">Indisponible</option>
            </select></label>
            <EdgeDetailsForm
              lengthM={Number(edgeLength)}
              geometry={edgeGeometry}
              onGeometryChange={setEdgeGeometry}
              profile={edgeProfile}
              onProfileChange={setEdgeProfile}
              fittings={edgeFittings}
              onFittingsChange={setEdgeFittings}
            />
            {edgeProblems.length ? (
              <div className="notice notice-error" role="alert">
                <ul className="issue-list negative">
                  {edgeProblems.map((problem) => (
                    <li key={problem}><span>{problem}</span></li>
                  ))}
                </ul>
              </div>
            ) : null}
            <button className="button button-primary" disabled={!editable || nodes.length < 2 || edgeMutation.isPending || edgeProblems.length > 0}>Ajouter le tronçon</button>
          </form>
        </details>
      </Panel>

      <Panel title="Équipements placés" description="Instances exactes des pompes, vannes et accessoires approuvés.">
        {assets.length ? (
          <div className="table-wrap"><table><thead><tr><th>Équipement</th><th>Référence</th><th>Emplacement</th><th>Rôle</th><th>Statut</th></tr></thead>
            <tbody>{assets.map((asset) => <tr key={asset.id}><td><strong>{asset.code}</strong><small>{asset.name}</small></td><td>{catalogNames.get(asset.catalog_item_id) ?? asset.catalog_item_id}</td><td>{asset.node_id ? nodeNames.get(asset.node_id) : edgeNames.get(asset.edge_id ?? "")}</td><td>{asset.role}</td><td><StatusBadge value={asset.status} /></td></tr>)}</tbody>
          </table></div>
        ) : <EmptyState title="Aucun équipement" detail="Approuvez une référence puis placez son instance dans le modèle." />}
        <details open={Boolean(placeableEquipment.length && !assets.length && editable)}>
          <summary>Placer un équipement</summary>
          <form className="compact-form" onSubmit={(event) => { event.preventDefault(); assetMutation.mutate(); }}>
            <label>Référence approuvée<select value={assetCatalogId} onChange={(event) => setAssetCatalogId(event.target.value)}><option value="">Sélectionner</option>{placeableEquipment.map((item) => <option key={item.id} value={item.id}>{item.code} — {item.name}</option>)}</select></label>
            <div className="form-grid">
              <label>Type d'emplacement<select value={assetLocationType} onChange={(event) => setAssetLocationType(event.target.value as "node" | "edge")}><option value="node">Nœud</option><option value="edge">Tronçon</option></select></label>
              <label>Emplacement<select value={assetLocationId} onChange={(event) => setAssetLocationId(event.target.value)}><option value="">Sélectionner</option>{(assetLocationType === "node" ? nodes : edges).map((item) => <option key={item.id} value={item.id}>{item.code} — {item.name}</option>)}</select></label>
            </div>
            <div className="form-grid three">
              <label>Code d'instance<input value={assetCode} onChange={(event) => setAssetCode(event.target.value.toUpperCase())} required /></label>
              <label>Nom<input value={assetName} onChange={(event) => setAssetName(event.target.value)} required /></label>
              <label>Rôle<select value={assetRole} onChange={(event) => setAssetRole(event.target.value as AssetInstance["role"])}><option value="main">Principal</option><option value="standby">Secours</option><option value="auxiliary">Auxiliaire</option><option value="isolation">Isolement</option><option value="control">Régulation</option><option value="measurement">Mesure</option></select></label>
            </div>
            <label>Paramètres d'installation<textarea className="code-editor compact-code" value={assetPayload} onChange={(event) => setAssetPayload(event.target.value)} rows={6} spellCheck={false} /></label>
            <button className="button button-primary" disabled={!editable || !assetCatalogId || !assetLocationId || assetMutation.isPending}>Placer l'équipement</button>
          </form>
        </details>
      </Panel>
    </div>
  );
}

/** Coordonnée géographique facultative : une chaîne vide reste absente. */
function optionalCoordinate(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
