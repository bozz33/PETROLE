import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { OrganizationField } from "../components/OrganizationField";
import { apiRequest, jsonBody } from "../api";
import {
  EmptyState,
  ErrorNotice,
  Panel,
  StatusBadge,
  SuccessNotice,
} from "../components/Shell";
import {
  defaultFluidPayload,
  FluidForm,
  validateFluid,
} from "../components/catalog/FluidForm";
import {
  AccessoryForm,
  defaultAccessoryPayload,
  defaultMaterialPayload,
  defaultValvePayload,
  MaterialForm,
  validateAccessory,
  validateMaterial,
  validateValve,
  ValveForm,
} from "../components/catalog/EquipmentForms";
import { defaultPumpPayload, PumpForm, validatePump } from "../components/catalog/PumpForm";
import { EXAMPLE_CATALOG_PAYLOADS } from "../samples";
import type {
  AccessoryPayload,
  CatalogCollection,
  CatalogItem,
  FluidPayload,
  MaterialPayload,
  Page,
  PumpPayload,
  ValvePayload,
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
  const [fluid, setFluid] = useState<FluidPayload>(defaultFluidPayload);
  const [pump, setPump] = useState<PumpPayload>(defaultPumpPayload);
  const [valve, setValve] = useState<ValvePayload>(defaultValvePayload);
  const [material, setMaterial] = useState<MaterialPayload>(defaultMaterialPayload);
  const [accessory, setAccessory] = useState<AccessoryPayload>(defaultAccessoryPayload);
  const [expertMode, setExpertMode] = useState(false);

  // Toutes les familles disposent désormais d'une fiche guidée ; la saisie JSON
  // reste accessible en mode expert.
  const useStructuredForm = !expertMode;
  const structuredPayload = (): Record<string, unknown> => {
    if (collection === "fluids") return fluid as unknown as Record<string, unknown>;
    if (collection === "pumps") return pump as unknown as Record<string, unknown>;
    if (collection === "valves") return valve as unknown as Record<string, unknown>;
    if (collection === "materials") return material as unknown as Record<string, unknown>;
    return accessory as unknown as Record<string, unknown>;
  };
  const structuredProblems = useStructuredForm ? validateCollection() : [];

  function validateCollection(): string[] {
    if (collection === "fluids") return validateFluid(fluid);
    if (collection === "pumps") return validatePump(pump);
    if (collection === "valves") return validateValve(valve);
    if (collection === "materials") return validateMaterial(material);
    return validateAccessory(accessory);
  }

  function resetStructured(): void {
    setFluid(defaultFluidPayload());
    setPump(defaultPumpPayload());
    setValve(defaultValvePayload());
    setMaterial(defaultMaterialPayload());
    setAccessory(defaultAccessoryPayload());
  }

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

  const items = itemsQuery.data?.items ?? [];


  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<CatalogItem>("/catalog/" + collection, {
        method: "POST",
        body: jsonBody({
          organization_id: organizationId,
          code,
          name,
          payload: useStructuredForm
            ? structuredPayload()
            : (JSON.parse(payload) as Record<string, unknown>),
          source: source || null,
        }),
      }),
    onSuccess: async () => {
      setCode("");
      setName("");
      setSource("");
      setPayload(examplePayload(collection));
      resetStructured();
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
          <OrganizationField value={organizationId} onChange={setOrganizationId} />
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
          <div className="button-row">
            <button
              type="button"
              className="button button-ghost"
              onClick={() => setExpertMode((current) => !current)}
            >
              {expertMode ? "Revenir au formulaire guidé" : "Passer en saisie JSON experte"}
            </button>
          </div>

          {useStructuredForm ? (
            <StructuredCatalogForm
              collection={collection}
              fluid={fluid}
              onFluidChange={setFluid}
              pump={pump}
              onPumpChange={setPump}
              valve={valve}
              onValveChange={setValve}
              material={material}
              onMaterialChange={setMaterial}
              accessory={accessory}
              onAccessoryChange={setAccessory}
            />
          ) : (
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
          )}

          {structuredProblems.length ? (
            <div className="notice notice-error" role="alert">
              <ul className="issue-list negative">
                {structuredProblems.map((problem) => (
                  <li key={problem}>
                    <span>{problem}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="button-row">
            <button
              className="button button-primary"
              disabled={
                !organizationId || createMutation.isPending || structuredProblems.length > 0
              }
            >
              Enregistrer le brouillon
            </button>
            {useStructuredForm ? (
              <button className="button button-ghost" type="button" onClick={resetStructured}>
                Réinitialiser la fiche
              </button>
            ) : (
              <button
                className="button button-ghost"
                type="button"
                onClick={() => setPayload(examplePayload(collection))}
              >
                Restaurer l'exemple
              </button>
            )}
          </div>
        </form>
      </Panel>
    </div>
  );
}

interface StructuredCatalogFormProps {
  collection: CatalogCollection;
  fluid: FluidPayload;
  onFluidChange: (value: FluidPayload) => void;
  pump: PumpPayload;
  onPumpChange: (value: PumpPayload) => void;
  valve: ValvePayload;
  onValveChange: (value: ValvePayload) => void;
  material: MaterialPayload;
  onMaterialChange: (value: MaterialPayload) => void;
  accessory: AccessoryPayload;
  onAccessoryChange: (value: AccessoryPayload) => void;
}

/** Sélectionne la fiche guidée correspondant à la famille du catalogue. */
function StructuredCatalogForm(props: StructuredCatalogFormProps) {
  switch (props.collection) {
    case "fluids":
      return <FluidForm value={props.fluid} onChange={props.onFluidChange} />;
    case "pumps":
      return <PumpForm value={props.pump} onChange={props.onPumpChange} />;
    case "valves":
      return <ValveForm value={props.valve} onChange={props.onValveChange} />;
    case "materials":
      return <MaterialForm value={props.material} onChange={props.onMaterialChange} />;
    default:
      return <AccessoryForm value={props.accessory} onChange={props.onAccessoryChange} />;
  }
}
