import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest, jsonBody } from "../api";
import {
  EmptyState,
  ErrorNotice,
  Panel,
  StatusBadge,
  SuccessNotice,
} from "../components/Shell";
import { EXAMPLE_CATALOG_PAYLOADS } from "../samples";
import type {
  CatalogCollection,
  CatalogItem,
  Organization,
  Page,
} from "../types";
import { formatDate } from "../types";

const COLLECTIONS: Array<{ value: CatalogCollection; label: string }> = [
  { value: "fluids", label: "Produits transportés" },
  { value: "pumps", label: "Pompes" },
  { value: "valves", label: "Vannes" },
  { value: "materials", label: "Matériaux" },
  { value: "accessories", label: "Accessoires" },
];

function examplePayload(collection: CatalogCollection): string {
  return JSON.stringify(EXAMPLE_CATALOG_PAYLOADS[collection], null, 2);
}

export function BibliothequesPage() {
  const queryClient = useQueryClient();
  const [organizationId, setOrganizationId] = useState("");
  const [collection, setCollection] = useState<CatalogCollection>("fluids");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [source, setSource] = useState("");
  const [payload, setPayload] = useState(examplePayload("fluids"));

  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<Page<Organization>>("/organizations?limit=200&offset=0"),
  });
  const itemsQuery = useQuery({
    queryKey: ["catalog", organizationId, collection],
    queryFn: () =>
      apiRequest<Page<CatalogItem>>(
        "/catalog/" +
          collection +
          "?limit=500&offset=0&organization_id=" +
          organizationId,
      ),
    enabled: Boolean(organizationId),
  });

  const organizations = organizationsQuery.data?.items ?? [];
  const items = itemsQuery.data?.items ?? [];

  useEffect(() => {
    if (!organizationId && organizations.length) {
      setOrganizationId(organizations[0].id);
    }
  }, [organizationId, organizations]);

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<CatalogItem>("/catalog/" + collection, {
        method: "POST",
        body: jsonBody({
          organization_id: organizationId,
          code,
          name,
          payload: JSON.parse(payload) as Record<string, unknown>,
          source: source || null,
        }),
      }),
    onSuccess: async () => {
      setCode("");
      setName("");
      setSource("");
      setPayload(examplePayload(collection));
      await queryClient.invalidateQueries({
        queryKey: ["catalog", organizationId, collection],
      });
    },
  });

  const approveMutation = useMutation({
    mutationFn: (itemId: string) =>
      apiRequest<CatalogItem>("/catalog/items/" + itemId + "/approve", {
        method: "POST",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["catalog", organizationId, collection],
      });
    },
  });

  const versionMutation = useMutation({
    mutationFn: (itemId: string) =>
      apiRequest<CatalogItem>("/catalog/items/" + itemId + "/versions", {
        method: "POST",
        body: jsonBody({}),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["catalog", organizationId, collection],
      });
    },
  });

  const error =
    organizationsQuery.error ??
    itemsQuery.error ??
    createMutation.error ??
    approveMutation.error ??
    versionMutation.error;
  const success =
    createMutation.isSuccess || approveMutation.isSuccess || versionMutation.isSuccess;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {success ? (
        <SuccessNotice>La version du catalogue a été enregistrée et auditée.</SuccessNotice>
      ) : null}

      <Panel
        title="Catalogue technique"
        description="Chaque ressource possède une source, une empreinte et un cycle d'approbation."
      >
        <div className="form-grid">
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
            Famille
            <select
              value={collection}
              onChange={(event) => {
                const nextCollection = event.target.value as CatalogCollection;
                setCollection(nextCollection);
                setPayload(examplePayload(nextCollection));
              }}
            >
              {COLLECTIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>

      <Panel
        title={COLLECTIONS.find((item) => item.value === collection)?.label ?? "Catalogue"}
        description={items.length + " version(s) disponible(s) dans cette organisation."}
      >
        {items.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ressource</th>
                  <th>Version</th>
                  <th>Source</th>
                  <th>Statut</th>
                  <th>Modification</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.code} — {item.name}</strong>
                      <small className="mono hash">{item.content_hash}</small>
                    </td>
                    <td>V{item.version_number}</td>
                    <td>{item.source ?? "Non renseignée"}</td>
                    <td><StatusBadge value={item.status} /></td>
                    <td>{formatDate(item.updated_at)}</td>
                    <td>
                      <div className="inline-actions">
                        {item.status === "draft" ? (
                          <button
                            className="button button-secondary"
                            onClick={() => approveMutation.mutate(item.id)}
                            disabled={approveMutation.isPending}
                          >
                            Approuver
                          </button>
                        ) : null}
                        {item.status === "approved" ? (
                          <button
                            className="button button-ghost"
                            onClick={() => versionMutation.mutate(item.id)}
                            disabled={versionMutation.isPending}
                          >
                            Nouvelle version
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Catalogue vide"
            detail="Créez la première version à partir d'une donnée vérifiable."
          />
        )}
      </Panel>

      <Panel
        title="Nouvelle ressource"
        description="La charge utile est validée par le backend scientifique avant enregistrement."
      >
        <form
          className="editor-form"
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate();
          }}
        >
          <div className="form-grid">
            <label>
              Code métier
              <input
                value={code}
                onChange={(event) => setCode(event.target.value.toUpperCase())}
                required
              />
            </label>
            <label>
              Nom
              <input value={name} onChange={(event) => setName(event.target.value)} required />
            </label>
          </div>
          <label>
            Source des données
            <input
              value={source}
              onChange={(event) => setSource(event.target.value)}
              placeholder="Analyse laboratoire, courbe constructeur ou fiche technique"
            />
          </label>
          <label>
            Propriétés techniques en unités SI
            <textarea
              className="code-editor"
              value={payload}
              onChange={(event) => setPayload(event.target.value)}
              spellCheck={false}
              rows={20}
            />
          </label>
          <div className="button-row">
            <button
              className="button button-primary"
              disabled={!organizationId || createMutation.isPending}
            >
              Enregistrer le brouillon
            </button>
            <button
              className="button button-ghost"
              type="button"
              onClick={() => setPayload(examplePayload(collection))}
            >
              Restaurer l'exemple
            </button>
          </div>
        </form>
      </Panel>
    </div>
  );
}
