import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { OrganizationField } from "../components/OrganizationField";
import { apiRequest, downloadApiFile, jsonBody } from "../api";
import { EmptyState, ErrorNotice, Panel, StatusBadge, SuccessNotice } from "../components/Shell";
import type {
  Dataset,
  DatasetImport,
  DatasetKind,
  DatasetPreview,
  Page,
  Project,
  StoredFile,
} from "../types";
import { formatDate, formatNumber } from "../types";

const FIELD_LABELS: Record<DatasetKind, Array<[string, string]>> = {
  profile: [
    ["chainage_m", "Chaînage (m)"],
    ["elevation_m", "Altitude (m)"],
  ],
  pump_curve: [
    ["flow_m3_s", "Débit (m³/s)"],
    ["head_m", "Hauteur (m)"],
    ["efficiency", "Rendement"],
    ["power_w", "Puissance (W)"],
    ["npshr_m", "NPSHr (m)"],
  ],
  strapping: [
    ["level_m", "Niveau (m)"],
    ["volume_m3", "Volume (m³)"],
  ],
  measurements: [
    ["timestamp", "Horodatage"],
    ["value", "Valeur"],
    ["unit", "Unité"],
    ["quality", "Qualité"],
    ["source", "Source"],
  ],
  generic: [],
};

const REQUIRED_FIELDS: Record<DatasetKind, Set<string>> = {
  profile: new Set(["chainage_m", "elevation_m"]),
  pump_curve: new Set(["flow_m3_s", "head_m"]),
  strapping: new Set(["level_m", "volume_m3"]),
  measurements: new Set(["timestamp", "value", "unit", "quality", "source"]),
  generic: new Set(),
};

const DEFAULT_UNITS: Record<DatasetKind, Record<string, string>> = {
  profile: { chainage_m: "m", elevation_m: "m" },
  pump_curve: {
    flow_m3_s: "m ** 3 / s",
    head_m: "m",
    efficiency: "dimensionless",
    power_w: "W",
    npshr_m: "m",
  },
  strapping: { level_m: "m", volume_m3: "m ** 3" },
  measurements: {},
  generic: {},
};

const MEASUREMENT_DIMENSIONS = [
  ["pressure", "Pression"],
  ["volumetric_flow", "Débit volumique"],
  ["mass_flow", "Débit massique"],
  ["temperature", "Température"],
  ["density", "Masse volumique"],
  ["length", "Niveau / longueur"],
  ["volume", "Volume"],
  ["power", "Puissance"],
  ["energy", "Énergie"],
] as const;

export function DonneesPage() {
  const [organizationId, setOrganizationId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState("");
  const [kind, setKind] = useState<DatasetKind>("profile");
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [units, setUnits] = useState<Record<string, string>>(DEFAULT_UNITS.profile);
  const [measurementDimension, setMeasurementDimension] = useState("pressure");
  const [importResult, setImportResult] = useState<DatasetImport | null>(null);

  const projectsQuery = useQuery({
    queryKey: ["projects", organizationId],
    queryFn: () =>
      apiRequest<Page<Project>>(
        "/projects?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });

  const projects = projectsQuery.data?.items ?? [];


  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) {
        throw new Error("Sélectionnez un fichier CSV, XLSX ou JSON.");
      }
      const form = new FormData();
      form.append("organization_id", organizationId);
      form.append("file", file);
      const storedFile = await apiRequest<StoredFile>("/files", {
        method: "POST",
        body: form,
      });
      return apiRequest<Dataset>("/datasets", {
        method: "POST",
        body: jsonBody({
          organization_id: organizationId,
          project_id: projectId || null,
          file_id: storedFile.id,
          name: datasetName || file.name,
          kind,
        }),
      });
    },
    onSuccess: async (createdDataset) => {
      setDataset(createdDataset);
      setPreview(null);
      setImportResult(null);
      const dataPreview = await apiRequest<DatasetPreview>(
        "/datasets/" + createdDataset.id + "/preview",
        { method: "POST" },
      );
      setPreview(dataPreview);
      setUnits(DEFAULT_UNITS[kind]);
      setMeasurementDimension("pressure");
      const proposed: Record<string, string> = {};
      for (const [field] of FIELD_LABELS[kind]) {
        const exact = dataPreview.columns.find(
          (column) => column.toLowerCase() === field.toLowerCase(),
        );
        if (exact) {
          proposed[field] = exact;
        }
      }
      setMapping(proposed);
    },
  });

  const mappingMutation = useMutation({
    mutationFn: () =>
      apiRequest<Dataset>("/datasets/" + dataset?.id + "/mappings", {
        method: "POST",
        body: jsonBody({
          fields: Object.fromEntries(
            Object.entries(mapping).filter(([, column]) => Boolean(column)),
          ),
          units: Object.fromEntries(
            Object.entries(units).filter(
              ([field, unit]) => Boolean(mapping[field]) && Boolean(unit.trim()),
            ),
          ),
          dimensions: kind === "measurements" ? { value: measurementDimension } : {},
        }),
      }),
    onSuccess: setDataset,
  });

  const importMutation = useMutation({
    mutationFn: () =>
      apiRequest<DatasetImport>("/datasets/" + dataset?.id + "/imports", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
      }),
    onSuccess: setImportResult,
  });

  const canMap = useMemo(
    () =>
      [...REQUIRED_FIELDS[kind]].every((field) => Boolean(mapping[field])),
    [kind, mapping],
  );
  const queryClient = useQueryClient();
  const documentsQuery = useQuery({
    queryKey: ["documents", organizationId],
    queryFn: () =>
      apiRequest<Page<StoredFile>>(
        "/documents?limit=100&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });
  const documents = documentsQuery.data?.items ?? [];

  const documentMutation = useMutation({
    mutationFn: async (form: FormData) => {
      const payload = new FormData();
      payload.set("organization_id", organizationId);
      const file = form.get("file");
      if (!(file instanceof File)) {
        throw new Error("Sélectionnez un document à joindre.");
      }
      payload.set("file", file);
      const description = String(form.get("description") ?? "").trim();
      if (description) {
        payload.set("description", description);
      }
      return apiRequest<StoredFile>("/documents", { method: "POST", body: payload });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["documents", organizationId] });
    },
  });

  const error =
    documentsQuery.error ??
    documentMutation.error ??
    projectsQuery.error ??
    uploadMutation.error ??
    mappingMutation.error ??
    importMutation.error;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {importResult ? (
        <SuccessNotice>
          Import terminé : {importResult.accepted_count} ligne(s) acceptée(s),{" "}
          {importResult.rejected_count} rejetée(s).
        </SuccessNotice>
      ) : null}

      <Panel
        title="1. Fichier source"
        description="Le fichier reste privé, haché et rattaché à son organisation."
      >
        <form
          className="form-grid three"
          onSubmit={(event) => {
            event.preventDefault();
            uploadMutation.mutate();
          }}
        >
          <OrganizationField value={organizationId} onChange={setOrganizationId} />
          <label>
            Projet, facultatif
            <select
              value={projectId}
              onChange={(event) => setProjectId(event.target.value)}
            >
              <option value="">Aucun projet</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.code} — {project.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Type de données
            <select
              value={kind}
              onChange={(event) => {
                const nextKind = event.target.value as DatasetKind;
                setKind(nextKind);
                setMapping({});
                setUnits(DEFAULT_UNITS[nextKind]);
                setMeasurementDimension("pressure");
              }}
            >
              <option value="profile">Profil altimétrique</option>
              <option value="pump_curve">Courbe de pompe</option>
              <option value="strapping">Barémage de bac</option>
              <option value="measurements">Mesures historiques</option>
              <option value="generic">Table générique</option>
            </select>
          </label>
          <label>
            Nom du jeu
            <input
              value={datasetName}
              onChange={(event) => setDatasetName(event.target.value)}
              placeholder="Profil ligne principale"
            />
          </label>
          <label className="file-field">
            Fichier CSV, XLSX ou JSON
            <input
              type="file"
              accept=".csv,.xlsx,.json,text/csv,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              required
            />
          </label>
          <div className="form-action">
            <button
              className="button button-primary"
              disabled={!organizationId || !file || uploadMutation.isPending}
            >
              {uploadMutation.isPending ? "Analyse en cours…" : "Téléverser et prévisualiser"}
            </button>
          </div>
        </form>
      </Panel>

      <Panel
        title="2. Aperçu et mapping"
        description="Aucune ligne n'est importée avant validation explicite des colonnes."
      >
        {preview ? (
          <div className="stack compact">
            <div className="mapping-grid">
              {FIELD_LABELS[kind].map(([field, label]) => (
                <label key={field}>
                  {label}
                  {REQUIRED_FIELDS[kind].has(field) ? <span className="required"> requis</span> : null}
                  <select
                    value={mapping[field] ?? ""}
                    onChange={(event) =>
                      setMapping((current) => ({
                        ...current,
                        [field]: event.target.value,
                      }))
                    }
                  >
                    <option value="">Non mappé</option>
                    {preview.columns.map((column) => (
                      <option key={column} value={column}>
                        {column} · {preview.detected_types[column]}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>

            {FIELD_LABELS[kind].some(([field]) => field !== "unit" && field !== "quality" && field !== "source" && field !== "timestamp") ? (
              <fieldset className="field-group">
                <legend>Unités source</legend>
                <p className="field-help">
                  Les valeurs sont converties en unités SI à l'import. L'unité déclarée reste associée à la ligne normalisée.
                </p>
                <div className="form-grid three">
                  {FIELD_LABELS[kind]
                    .filter(([field]) => !["unit", "quality", "source", "timestamp"].includes(field))
                    .map(([field, label]) => (
                      <label key={field}>
                        {label}
                        {kind === "measurements" && field === "value" ? (
                          <small>Provient de la colonne mappée « Unité ».</small>
                        ) : null}
                        <input
                          value={units[field] ?? ""}
                          placeholder={kind === "measurements" && field === "value" ? "unité par ligne" : "m"}
                          disabled={kind === "measurements" && field === "value"}
                          onChange={(event) =>
                            setUnits((current) => ({ ...current, [field]: event.target.value }))
                          }
                        />
                      </label>
                    ))}
                  {kind === "measurements" ? (
                    <label>
                      Grandeur mesurée
                      <select
                        value={measurementDimension}
                        onChange={(event) => setMeasurementDimension(event.target.value)}
                      >
                        {MEASUREMENT_DIMENSIONS.map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                </div>
              </fieldset>
            ) : null}

            <div className="preview-meta">
              <strong>{formatNumber(preview.row_count, 0)} lignes détectées</strong>
              <span>{preview.columns.length} colonnes</span>
              {dataset ? <StatusBadge value={dataset.status} /> : null}
            </div>
            <PreviewTable preview={preview} />

            <div className="button-row">
              <button
                className="button button-primary"
                disabled={!canMap || mappingMutation.isPending}
                onClick={() => mappingMutation.mutate()}
              >
                Valider le mapping
              </button>
              <button
                className="button button-secondary"
                disabled={dataset?.status !== "mapped" || importMutation.isPending}
                onClick={() => importMutation.mutate()}
              >
                Importer les lignes
              </button>
            </div>
          </div>
        ) : (
          <EmptyState
            title="Aucun aperçu"
            detail="Téléversez un fichier pour détecter ses colonnes et ses types."
          />
        )}
      </Panel>

      <Panel
        title="3. Rapport d'import"
        description="Les lignes rejetées restent consultables avec leur cause."
      >
        {importResult ? (
          <div className="stack compact">
            <div className="metrics-grid">
              <ImportMetric label="Lignes" value={importResult.row_count} />
              <ImportMetric label="Acceptées" value={importResult.accepted_count} />
              <ImportMetric label="Rejetées" value={importResult.rejected_count} />
              <article className="metric-card blue">
                <p>Statut</p>
                <StatusBadge value={importResult.status} />
                <small className="mono hash">{importResult.content_hash}</small>
              </article>
            </div>
            {importResult.errors.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Ligne</th>
                      <th>Champ</th>
                      <th>Code</th>
                      <th>Cause</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importResult.errors.map((item, index) => (
                      <tr key={String(item.row) + item.field + index}>
                        <td>{item.row}</td>
                        <td>{item.field}</td>
                        <td className="mono">{item.code}</td>
                        <td>{item.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="Import sans erreur"
                detail="Toutes les lignes ont satisfait les contrôles configurés."
              />
            )}
          </div>
        ) : (
          <EmptyState
            title="Import non exécuté"
            detail="Validez le mapping puis lancez la normalisation."
          />
        )}
      </Panel>

      <Panel
        title="Pièces jointes du projet"
        description="Fiches constructeur, plans, notes et rapports, conservés tels quels."
      >
        <form
          className="compact-form"
          onSubmit={(event) => {
            event.preventDefault();
            documentMutation.mutate(new FormData(event.currentTarget));
          }}
        >
          <div className="form-grid">
            <label>
              Document
              <input
                name="file"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.xlsx,.docx,.csv,.txt"
                required
              />
              <small>PDF, image, classeur, document texte. Ces fichiers ne sont pas importés comme données.</small>
            </label>
            <label>
              Description
              <input name="description" placeholder="Fiche constructeur P-101" />
            </label>
          </div>
          <button
            className="button button-primary"
            disabled={!organizationId || documentMutation.isPending}
          >
            {documentMutation.isPending ? "Téléversement…" : "Joindre le document"}
          </button>
        </form>

        {documents.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Type</th>
                  <th>Taille</th>
                  <th>Empreinte</th>
                  <th>Ajouté le</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr key={document.id}>
                    <td>
                      <strong>{document.filename}</strong>
                      <small>{document.description ?? "Sans description"}</small>
                    </td>
                    <td>{document.media_type}</td>
                    <td>{formatNumber(document.size_bytes / 1024, 1)} Kio</td>
                    <td className="mono hash">{document.content_hash.slice(0, 24)}…</td>
                    <td>{formatDate(document.created_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="button button-ghost"
                        onClick={() =>
                          void downloadApiFile(
                            "/files/" + document.id + "/download",
                            document.filename,
                          )
                        }
                      >
                        Télécharger
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Aucune pièce jointe"
            detail="Joignez les documents constructeur et les notes techniques du projet."
          />
        )}
      </Panel>
    </div>
  );
}

function PreviewTable({ preview }: { preview: DatasetPreview }) {
  return (
    <div className="table-wrap preview-table">
      <table>
        <thead>
          <tr>
            {preview.columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {preview.rows.slice(0, 10).map((row, rowIndex) => (
            <tr key={rowIndex}>
              {preview.columns.map((column) => (
                <td key={column}>{String(row[column] ?? "—")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ImportMetric({ label, value }: { label: string; value: number }) {
  return (
    <article className="metric-card green">
      <p>{label}</p>
      <strong>{formatNumber(value, 0)}</strong>
      <small>ligne(s)</small>
    </article>
  );
}
