/**
 * Panneau de propriétés de l'élément sélectionné dans le schéma.
 *
 * L'édition reste volontairement limitée à ce qui se règle sans recomposer le
 * réseau : état d'exploitation, altitude, coordonnées. Créer ou reconnecter un
 * tronçon passe par l'écran Modélisation, où les contrôles de continuité et de
 * profil s'appliquent intégralement.
 */

import { useEffect, useState } from "react";

import { EmptyState, StatusBadge } from "@/components/Shell";
import type {
  AssetInstance,
  NetworkEdge,
  NetworkNode,
  NetworkValidationIssue,
} from "@/types";
import { formatNumber } from "@/types";

const NODE_KIND_LABELS: Record<NetworkNode["kind"], string> = {
  source: "Source",
  tank: "Raccordement de bac",
  station: "Station de pompage",
  junction: "Jonction",
  terminal: "Terminal",
  injection: "Injection",
  offtake: "Soutirage",
};

const STATUS_LABELS: Record<string, string> = {
  available: "Disponible",
  maintenance: "En maintenance",
  unavailable: "Indisponible",
  bypassed: "Contourné",
};

export interface NodePatch {
  status?: NetworkNode["status"];
  elevation_m?: number;
  latitude?: number | null;
  longitude?: number | null;
  /** Position du nœud sur le schéma, conservée avec le modèle. */
  payload?: Record<string, unknown>;
}

export interface EdgePatch {
  status?: NetworkEdge["status"];
}

const ASSET_ROLE_LABELS: Record<AssetInstance["role"], string> = {
  main: "Principal",
  standby: "Secours",
  auxiliary: "Auxiliaire",
  isolation: "Isolement",
  control: "Régulation",
  measurement: "Mesure",
};

interface ElementInspectorProps {
  node: NetworkNode | null;
  edge: NetworkEdge | null;
  asset: AssetInstance | null;
  nodes: NetworkNode[];
  issues: NetworkValidationIssue[];
  editable: boolean;
  pending: boolean;
  onPatchNode: (nodeId: string, patch: NodePatch) => void;
  onPatchEdge: (edgeId: string, patch: EdgePatch) => void;
}

export function ElementInspector({
  node,
  edge,
  asset,
  nodes,
  issues,
  editable,
  pending,
  onPatchNode,
  onPatchEdge,
}: ElementInspectorProps) {
  if (!node && !edge && !asset) {
    return (
      <EmptyState
        title="Aucun élément sélectionné"
        detail="Cliquez sur un nœud, un tronçon ou un équipement du schéma pour afficher ses propriétés."
      />
    );
  }

  const selectedId = node?.id ?? edge?.id ?? asset?.id ?? "";
  const elementIssues = issues.filter((issue) => issue.object_id === selectedId);

  return (
    <div className="stack">
      {node ? (
        <NodeInspector node={node} editable={editable} pending={pending} onPatch={onPatchNode} />
      ) : null}
      {edge ? (
        <EdgeInspector
          edge={edge}
          nodes={nodes}
          editable={editable}
          pending={pending}
          onPatch={onPatchEdge}
        />
      ) : null}
      {asset ? <AssetInspector asset={asset} nodes={nodes} /> : null}

      {elementIssues.length ? (
        <ul className="issue-list negative">
          {elementIssues.map((issue) => (
            <li key={issue.code + issue.message}>
              <strong>{issue.code}</strong>
              <span>{issue.message}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function NodeInspector({
  node,
  editable,
  pending,
  onPatch,
}: {
  node: NetworkNode;
  editable: boolean;
  pending: boolean;
  onPatch: (nodeId: string, patch: NodePatch) => void;
}) {
  const [elevation, setElevation] = useState(String(node.elevation_m));
  const [latitude, setLatitude] = useState(node.latitude === null ? "" : String(node.latitude));
  const [longitude, setLongitude] = useState(
    node.longitude === null ? "" : String(node.longitude),
  );

  useEffect(() => {
    setElevation(String(node.elevation_m));
    setLatitude(node.latitude === null ? "" : String(node.latitude));
    setLongitude(node.longitude === null ? "" : String(node.longitude));
  }, [node]);

  return (
    <>
      <div className="resource-summary">
        <div>
          <span>Nœud</span>
          <strong>
            {node.code} — {node.name}
          </strong>
        </div>
        <div>
          <span>Type</span>
          <strong>{NODE_KIND_LABELS[node.kind]}</strong>
        </div>
        <div>
          <span>État</span>
          <StatusBadge value={STATUS_LABELS[node.status] ?? node.status} />
        </div>
      </div>

      <div className="form-grid three">
        <label>
          Altitude (m)
          <input
            type="number"
            step="any"
            value={elevation}
            disabled={!editable}
            onChange={(event) => setElevation(event.target.value)}
          />
        </label>
        <label>
          Latitude
          <input
            type="number"
            step="any"
            min="-90"
            max="90"
            value={latitude}
            disabled={!editable}
            onChange={(event) => setLatitude(event.target.value)}
          />
        </label>
        <label>
          Longitude
          <input
            type="number"
            step="any"
            min="-180"
            max="180"
            value={longitude}
            disabled={!editable}
            onChange={(event) => setLongitude(event.target.value)}
          />
        </label>
      </div>

      {editable ? (
        <div className="button-row">
          <button
            type="button"
            className="button button-primary"
            disabled={pending}
            onClick={() =>
              onPatch(node.id, {
                elevation_m: Number(elevation),
                latitude: optionalNumber(latitude),
                longitude: optionalNumber(longitude),
              })
            }
          >
            Enregistrer la position
          </button>
          {(["available", "maintenance", "unavailable"] as const)
            .filter((status) => status !== node.status)
            .map((status) => (
              <button
                key={status}
                type="button"
                className="button button-ghost"
                disabled={pending}
                onClick={() => onPatch(node.id, { status })}
              >
                Passer en « {STATUS_LABELS[status].toLowerCase()} »
              </button>
            ))}
        </div>
      ) : (
        <p className="field-help">
          Cette version de modèle est approuvée : son réseau est figé et ne peut plus être
          modifié.
        </p>
      )}
    </>
  );
}

function EdgeInspector({
  edge,
  nodes,
  editable,
  pending,
  onPatch,
}: {
  edge: NetworkEdge;
  nodes: NetworkNode[];
  editable: boolean;
  pending: boolean;
  onPatch: (edgeId: string, patch: EdgePatch) => void;
}) {
  const origin = nodes.find((item) => item.id === edge.from_node_id);
  const destination = nodes.find((item) => item.id === edge.to_node_id);
  const geometry = edge.payload as {
    outer_diameter_m?: number | null;
    wall_thickness_m?: number | null;
    minimum_pressure_pa?: number | null;
  };

  return (
    <>
      <div className="resource-summary">
        <div>
          <span>Tronçon</span>
          <strong>
            {edge.code} — {edge.name}
          </strong>
        </div>
        <div>
          <span>Trajet</span>
          <strong>
            {origin?.code ?? "?"} → {destination?.code ?? "?"}
          </strong>
        </div>
        <div>
          <span>État</span>
          <StatusBadge value={STATUS_LABELS[edge.status] ?? edge.status} />
        </div>
        <div>
          <span>Longueur</span>
          <strong>{formatNumber(edge.length_m / 1000, 3)} km</strong>
        </div>
        <div>
          <span>Diamètre intérieur</span>
          <strong>{formatNumber(edge.inner_diameter_m * 1000, 1)} mm</strong>
        </div>
        <div>
          <span>Diamètre extérieur</span>
          <strong>
            {geometry.outer_diameter_m
              ? `${formatNumber(geometry.outer_diameter_m * 1000, 1)} mm`
              : "—"}
          </strong>
        </div>
        <div>
          <span>Épaisseur</span>
          <strong>
            {geometry.wall_thickness_m
              ? `${formatNumber(geometry.wall_thickness_m * 1000, 1)} mm`
              : "—"}
          </strong>
        </div>
        <div>
          <span>Rugosité</span>
          <strong>{formatNumber(edge.roughness_m * 1000, 4)} mm</strong>
        </div>
        <div>
          <span>Pression maximale</span>
          <strong>{formatNumber(edge.mawp_pa / 100000, 2)} bar</strong>
        </div>
        <div>
          <span>Pression minimale</span>
          <strong>
            {geometry.minimum_pressure_pa
              ? `${formatNumber(geometry.minimum_pressure_pa / 100000, 2)} bar`
              : "—"}
          </strong>
        </div>
        <div>
          <span>Points de profil</span>
          <strong>{edge.profile_payload.length}</strong>
        </div>
        <div>
          <span>Accessoires</span>
          <strong>{edge.fittings_payload.length}</strong>
        </div>
      </div>

      {editable ? (
        <div className="button-row">
          {(["available", "maintenance", "unavailable"] as const)
            .filter((status) => status !== edge.status)
            .map((status) => (
              <button
                key={status}
                type="button"
                className="button button-ghost"
                disabled={pending}
                onClick={() => onPatch(edge.id, { status })}
              >
                Passer en « {STATUS_LABELS[status].toLowerCase()} »
              </button>
            ))}
        </div>
      ) : null}
    </>
  );
}

function optionalNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}


function AssetInspector({ asset, nodes }: { asset: AssetInstance; nodes: NetworkNode[] }) {
  const host = nodes.find((item) => item.id === asset.node_id);

  return (
    <div className="resource-summary">
      <div>
        <span>Équipement</span>
        <strong>
          {asset.code} — {asset.name}
        </strong>
      </div>
      <div>
        <span>Rôle</span>
        <strong>{ASSET_ROLE_LABELS[asset.role]}</strong>
      </div>
      <div>
        <span>État</span>
        <StatusBadge value={STATUS_LABELS[asset.status] ?? asset.status} />
      </div>
      <div>
        <span>Emplacement</span>
        <strong>{host ? `Nœud ${host.code}` : "Sur un tronçon"}</strong>
      </div>
      <div>
        <span>Référence de catalogue</span>
        <strong className="mono">{asset.catalog_item_id.slice(0, 8)}</strong>
      </div>
    </div>
  );
}
