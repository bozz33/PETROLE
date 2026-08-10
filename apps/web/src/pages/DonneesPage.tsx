import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { OrganizationField } from "../components/OrganizationField";
import { apiRequest, downloadApiFile, jsonBody } from "../api";
import { TimeSeriesChart } from "../components/charts/TimeSeriesChart";
import { EmptyState, ErrorNotice, Panel, StatusBadge, SuccessNotice } from "../components/Shell";
import type {
  Dataset,
  DatasetImport,
  DatasetKind,
  DatasetPreview,
  MeasurementTag,
  OutlierMethod,
  Page,
  ProcessingVersion,
  Project,
  SampleQuality,
  SeriesAnalysis,
  Site,
  StoredFile,
} from "../types";
import { formatDate, formatNumber } from "../types";

const EMPTY_SITES: Site[] = [];
const EMPTY_MEASUREMENT_TAGS: MeasurementTag[] = [];
const EMPTY_PROCESSING_VERSIONS: ProcessingVersion[] = [];
const SERIES_PAGE_SIZE = 500;
const DEFAULT_SERIES_QUALITIES: SampleQuality[] = [
  "good",
  "uncertain",
  "substituted",
  "estimated",
];
const SERIES_QUALITY_LABELS: Record<SampleQuality, string> = {
  good: "Bonne",
  uncertain: "Incertaine",
  bad: "Mauvaise",
  substituted: "Substituée",
  estimated: "Estimée",
};

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

function optionalPositiveNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function toUtcQuery(value: string): string | null {
  if (!value) {
    return null;
  }
  // `datetime-local` ne porte aucun fuseau. Le contrat de cette page est UTC,
  // donc 10:00 saisi ici signifie explicitement 10:00Z et non l'heure locale
  // variable du navigateur.
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`;
  const timestamp = new Date(normalized);
  return Number.isNaN(timestamp.getTime()) ? null : timestamp.toISOString();
}

function formatInterval(value: number | null): string {
  if (value === null) {
    return "Non déterminée";
  }
  if (value < 60) {
    return `${formatNumber(value, 1)} s`;
  }
  if (value < 3600) {
    return `${formatNumber(value / 60, 1)} min`;
  }
  return `${formatNumber(value / 3600, 2)} h`;
}

export interface SeriesAnalysisRequest {
  processingVersion: string;
  startTimestamp: string;
  endTimestamp: string;
  qualities: SampleQuality[];
  referenceInterval: string;
  gapFactor: string;
  outlierMethod: OutlierMethod;
  outlierThreshold: string;
  offset: number;
}

/** Construit un appel explicite : une analyse ne mélange jamais deux projections. */
export function buildSeriesAnalysisPath(
  tagId: string,
  request: SeriesAnalysisRequest,
): string | null {
  if (!tagId || !request.processingVersion) {
    return null;
  }
  const requestedGapFactor = optionalPositiveNumber(request.gapFactor);
  const gapFactor = requestedGapFactor !== null && requestedGapFactor > 1 ? requestedGapFactor : 1.5;
  const parameters = new URLSearchParams({
    processing_version: request.processingVersion,
    gap_factor: String(gapFactor),
    outlier_method: request.outlierMethod,
    zscore_threshold: String(
      request.outlierMethod === "zscore" ? optionalPositiveNumber(request.outlierThreshold) ?? 3 : 3,
    ),
    iqr_multiplier: String(
      request.outlierMethod === "iqr" ? optionalPositiveNumber(request.outlierThreshold) ?? 1.5 : 1.5,
    ),
    limit: String(SERIES_PAGE_SIZE),
    offset: String(request.offset),
  });
  const startTimestamp = toUtcQuery(request.startTimestamp);
  const endTimestamp = toUtcQuery(request.endTimestamp);
  const referenceInterval = optionalPositiveNumber(request.referenceInterval);
  if (startTimestamp) {
    parameters.set("start_timestamp", startTimestamp);
  }
  if (endTimestamp) {
    parameters.set("end_timestamp", endTimestamp);
  }
  if (referenceInterval !== null) {
    parameters.set("reference_interval_seconds", String(referenceInterval));
  }
  for (const quality of request.qualities) {
    parameters.append("qualities", quality);
  }
  return "/measurement-tags/" + tagId + "/series-analysis?" + parameters.toString();
}

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
  const [seriesSiteId, setSeriesSiteId] = useState("");
  const [seriesTagId, setSeriesTagId] = useState("");
  const [seriesProcessingVersion, setSeriesProcessingVersion] = useState("");
  const [seriesStartTimestamp, setSeriesStartTimestamp] = useState("");
  const [seriesEndTimestamp, setSeriesEndTimestamp] = useState("");
  const [seriesQualities, setSeriesQualities] = useState<SampleQuality[]>(
    DEFAULT_SERIES_QUALITIES,
  );
  const [seriesReferenceInterval, setSeriesReferenceInterval] = useState("");
  const [seriesGapFactor, setSeriesGapFactor] = useState("1.5");
  const [seriesOutlierMethod, setSeriesOutlierMethod] = useState<OutlierMethod>("none");
  const [seriesOutlierThreshold, setSeriesOutlierThreshold] = useState("3");
  const [seriesOffset, setSeriesOffset] = useState(0);

  const projectsQuery = useQuery({
    queryKey: ["projects", organizationId],
    queryFn: () =>
      apiRequest<Page<Project>>(
        "/projects?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });

  const projects = projectsQuery.data?.items ?? [];

  const sitesQuery = useQuery({
    queryKey: ["sites", organizationId],
    queryFn: () =>
      apiRequest<Page<Site>>(
        "/sites?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });
  const sites = sitesQuery.data?.items ?? EMPTY_SITES;
  const selectedSeriesSiteId =
    seriesSiteId && sites.some((site) => site.id === seriesSiteId)
      ? seriesSiteId
      : (sites[0]?.id ?? "");
  const measurementTagsQuery = useQuery({
    queryKey: ["measurement-tags", organizationId, selectedSeriesSiteId],
    queryFn: () =>
      apiRequest<Page<MeasurementTag>>(
        "/measurement-tags?limit=200&offset=0&organization_id=" +
          organizationId +
          "&site_id=" +
          selectedSeriesSiteId,
      ),
    enabled: Boolean(organizationId && selectedSeriesSiteId),
  });
  const measurementTags = measurementTagsQuery.data?.items ?? EMPTY_MEASUREMENT_TAGS;
  const selectedSeriesTagId =
    seriesTagId && measurementTags.some((tag) => tag.id === seriesTagId)
      ? seriesTagId
      : (measurementTags[0]?.id ?? "");
  const processingVersionsQuery = useQuery({
    queryKey: ["measurement-processing-versions", selectedSeriesTagId],
    queryFn: () =>
      apiRequest<ProcessingVersion[]>(
        "/measurement-tags/" + selectedSeriesTagId + "/processing-versions",
      ),
    enabled: Boolean(selectedSeriesTagId),
  });
  const processingVersions = processingVersionsQuery.data ?? EMPTY_PROCESSING_VERSIONS;
  const selectedProcessingVersion =
    seriesProcessingVersion &&
    processingVersions.some((version) => version.processing_version === seriesProcessingVersion)
      ? seriesProcessingVersion
      : (processingVersions[0]?.processing_version ?? "");
  const seriesAnalysisPath = useMemo(() => {
    return buildSeriesAnalysisPath(selectedSeriesTagId, {
      processingVersion: selectedProcessingVersion,
      startTimestamp: seriesStartTimestamp,
      endTimestamp: seriesEndTimestamp,
      qualities: seriesQualities,
      referenceInterval: seriesReferenceInterval,
      gapFactor: seriesGapFactor,
      outlierMethod: seriesOutlierMethod,
      outlierThreshold: seriesOutlierThreshold,
      offset: seriesOffset,
    });
  }, [
    selectedSeriesTagId,
    selectedProcessingVersion,
    seriesEndTimestamp,
    seriesGapFactor,
    seriesOffset,
    seriesOutlierMethod,
    seriesOutlierThreshold,
    seriesQualities,
    seriesReferenceInterval,
    seriesStartTimestamp,
  ]);
  const seriesAnalysisQuery = useQuery({
    queryKey: ["measurement-series-analysis", selectedSeriesTagId, seriesAnalysisPath],
    queryFn: () => apiRequest<SeriesAnalysis>(seriesAnalysisPath ?? ""),
    enabled: Boolean(seriesAnalysisPath),
  });
  const seriesAnalysis = seriesAnalysisQuery.data;


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
    seriesAnalysisQuery.error ??
    processingVersionsQuery.error ??
    measurementTagsQuery.error ??
    sitesQuery.error ??
    projectsQuery.error ??
    uploadMutation.error ??
    mappingMutation.error ??
    importMutation.error;

  const toggleSeriesQuality = (quality: SampleQuality) => {
    setSeriesQualities((current) => {
      if (!current.includes(quality)) {
        return [...current, quality];
      }
      // L'absence du paramètre `qualities` signifie le filtre par défaut dans
      // l'API. Garder un choix actif évite de transformer silencieusement une
      // sélection vide en un autre jeu de points.
      return current.length === 1 ? current : current.filter((item) => item !== quality);
    });
    setSeriesOffset(0);
  };

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
        title="4. Séries temporelles et qualité"
        description="Explorer une projection SI versionnée sans modifier le brut, les lignes importées ni les points signalés."
      >
        {!organizationId ? (
          <EmptyState
            title="Sélectionnez un exploitant"
            detail="Les tags de mesure restent rattachés à leur organisation et à leur site."
          />
        ) : !sitesQuery.isPending && !sites.length ? (
          <EmptyState
            title="Aucun site disponible"
            detail="Créez ou importez un site avant de rattacher des tags de mesure."
          />
        ) : (
          <div className="stack compact">
            <div className="form-grid three">
              <label>
                Site
                <select
                  aria-label="Site de la série"
                  value={selectedSeriesSiteId}
                  onChange={(event) => {
                    setSeriesSiteId(event.target.value);
                    setSeriesTagId("");
                    setSeriesProcessingVersion("");
                    setSeriesOffset(0);
                  }}
                >
                  {sites.map((site) => (
                    <option key={site.id} value={site.id}>
                      {site.code} — {site.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Tag
                <select
                  aria-label="Tag de mesure"
                  value={selectedSeriesTagId}
                  disabled={!measurementTags.length}
                  onChange={(event) => {
                    setSeriesTagId(event.target.value);
                    setSeriesProcessingVersion("");
                    setSeriesOffset(0);
                  }}
                >
                  {!measurementTags.length ? <option value="">Aucun tag</option> : null}
                  {measurementTags.map((tag) => (
                    <option key={tag.id} value={tag.id}>
                      {tag.external_name} — {tag.name} ({tag.si_unit})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Version de traitement
                <select
                  aria-label="Version de traitement"
                  value={selectedProcessingVersion}
                  disabled={!processingVersions.length}
                  onChange={(event) => {
                    setSeriesProcessingVersion(event.target.value);
                    setSeriesOffset(0);
                  }}
                >
                  {!processingVersions.length ? <option value="">Aucune projection</option> : null}
                  {processingVersions.map((version) => (
                    <option key={version.processing_version} value={version.processing_version}>
                      {version.processing_version} · {formatNumber(version.sample_count, 0)} points
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Début UTC, facultatif
                <input
                  type="datetime-local"
                  value={seriesStartTimestamp}
                  onChange={(event) => {
                    setSeriesStartTimestamp(event.target.value);
                    setSeriesOffset(0);
                  }}
                />
              </label>
              <label>
                Fin UTC, facultative
                <input
                  type="datetime-local"
                  value={seriesEndTimestamp}
                  onChange={(event) => {
                    setSeriesEndTimestamp(event.target.value);
                    setSeriesOffset(0);
                  }}
                />
              </label>
              <label>
                Cadence de référence (s), facultative
                <input
                  type="number"
                  min="0.001"
                  step="any"
                  value={seriesReferenceInterval}
                  placeholder="Médiane observée"
                  onChange={(event) => {
                    setSeriesReferenceInterval(event.target.value);
                    setSeriesOffset(0);
                  }}
                />
              </label>
              <label>
                Facteur de trou
                <input
                  type="number"
                  min="1.01"
                  step="0.1"
                  value={seriesGapFactor}
                  onChange={(event) => {
                    setSeriesGapFactor(event.target.value);
                    setSeriesOffset(0);
                  }}
                />
                <small>Un trou dépasse cadence × facteur.</small>
              </label>
              <label>
                Méthode d&apos;aberrants
                <select
                  value={seriesOutlierMethod}
                  onChange={(event) => {
                    const method = event.target.value as OutlierMethod;
                    setSeriesOutlierMethod(method);
                    setSeriesOutlierThreshold(method === "iqr" ? "1.5" : "3");
                    setSeriesOffset(0);
                  }}
                >
                  <option value="none">Aucune</option>
                  <option value="zscore">Z-score</option>
                  <option value="iqr">IQR</option>
                </select>
              </label>
              <label>
                {seriesOutlierMethod === "iqr" ? "Facteur IQR" : "Seuil z-score"}
                <input
                  type="number"
                  min="0.001"
                  step="0.1"
                  disabled={seriesOutlierMethod === "none"}
                  value={seriesOutlierThreshold}
                  onChange={(event) => {
                    setSeriesOutlierThreshold(event.target.value);
                    setSeriesOffset(0);
                  }}
                />
                <small>Détection seulement : aucun point n&apos;est supprimé.</small>
              </label>
            </div>

            <fieldset className="field-group">
              <legend>Qualités visibles et incluses dans les statistiques</legend>
              <div className="checkbox-row">
                {(Object.keys(SERIES_QUALITY_LABELS) as SampleQuality[]).map((quality) => (
                  <label key={quality} className="checkbox-field">
                    <input
                      type="checkbox"
                      checked={seriesQualities.includes(quality)}
                      onChange={() => toggleSeriesQuality(quality)}
                    />
                    {SERIES_QUALITY_LABELS[quality]}
                  </label>
                ))}
              </div>
              <p className="field-help">
                Les mesures mauvaises sont conservées. Elles sont exclues par défaut, mais peuvent
                être affichées explicitement.
              </p>
            </fieldset>

            {!measurementTagsQuery.isPending && !measurementTags.length ? (
              <EmptyState
                title="Aucun tag pour ce site"
                detail="Projetez d'abord un dataset de mesures figé vers un tag du site."
              />
            ) : seriesAnalysisQuery.isPending ? (
              <EmptyState
                title="Analyse temporelle en cours"
                detail="Les diagnostics sont calculés en lecture seule sur la projection sélectionnée."
              />
            ) : seriesAnalysis ? (
              <SeriesAnalysisPanel
                analysis={seriesAnalysis}
                onPreviousPage={() =>
                  setSeriesOffset((current) => Math.max(0, current - SERIES_PAGE_SIZE))
                }
                onNextPage={() => setSeriesOffset((current) => current + SERIES_PAGE_SIZE)}
              />
            ) : (
              <EmptyState
                title="Aucune projection à explorer"
                detail="Choisissez un tag et une version de traitement pour obtenir une série SI traçable."
              />
            )}
          </div>
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

function SeriesAnalysisPanel({
  analysis,
  onPreviousPage,
  onNextPage,
}: {
  analysis: SeriesAnalysis;
  onPreviousPage: () => void;
  onNextPage: () => void;
}) {
  const pageStart = analysis.total ? analysis.offset + 1 : 0;
  const pageEnd = Math.min(analysis.offset + analysis.items.length, analysis.total);

  if (!analysis.total) {
    return (
      <EmptyState
        title="Aucun point pour ces filtres"
        detail="Les données sources sont conservées ; élargissez la période ou les qualités visibles."
      />
    );
  }

  return (
    <div className="stack compact">
      <div className="preview-meta">
        <strong>
          {analysis.tag.external_name} — {analysis.tag.name}
        </strong>
        <span className="mono">{analysis.processing_version}</span>
        <span>{analysis.tag.si_unit}</span>
        <span>
          {formatDate(analysis.start_timestamp)} → {formatDate(analysis.end_timestamp)}
        </span>
      </div>

      <TimeSeriesChart
        points={analysis.items}
        siUnit={analysis.tag.si_unit}
        processingVersion={analysis.processing_version}
      />
      {analysis.total > analysis.items.length ? (
        <p className="field-help">
          Le graphique montre la page consultée ({formatNumber(pageStart, 0)}–
          {formatNumber(pageEnd, 0)}) ; la table permet de parcourir les autres points.
        </p>
      ) : null}

      <div className="metrics-grid">
        <SeriesMetric
          label="Points visibles"
          value={formatNumber(analysis.statistics.sample_count, 0)}
          detail={`${formatNumber(analysis.excluded_sample_count, 0)} exclu(s) par filtre`}
          tone="green"
        />
        <SeriesMetric
          label="Moyenne SI"
          value={
            analysis.statistics.mean_value_si === null
              ? "—"
              : formatNumber(analysis.statistics.mean_value_si)
          }
          detail={analysis.tag.si_unit}
          tone="blue"
        />
        <SeriesMetric
          label="Écart-type SI"
          value={
            analysis.statistics.stddev_value_si === null
              ? "—"
              : formatNumber(analysis.statistics.stddev_value_si)
          }
          detail={analysis.tag.si_unit}
          tone="blue"
        />
        <SeriesMetric
          label="Doublons"
          value={formatNumber(analysis.duplicate_timestamp_count, 0)}
          detail="Horodatages conservés"
          tone="amber"
        />
        <SeriesMetric
          label="Trous"
          value={formatNumber(analysis.gap_count, 0)}
          detail={`Cadence ${formatInterval(analysis.reference_interval_seconds)}`}
          tone="amber"
        />
        <SeriesMetric
          label="Aberrants signalés"
          value={formatNumber(analysis.outlier_count, 0)}
          detail={
            analysis.outlier_method === "none"
              ? "Détection désactivée"
              : `${analysis.outlier_method} · seuil ${formatNumber(analysis.outlier_threshold ?? 0, 2)}`
          }
          tone="purple"
        />
      </div>

      <div className="detail-list">
        <div>
          <dt>Minimum / maximum SI</dt>
          <dd>
            {analysis.statistics.minimum_value_si === null
              ? "—"
              : formatNumber(analysis.statistics.minimum_value_si)}
            {" / "}
            {analysis.statistics.maximum_value_si === null
              ? "—"
              : formatNumber(analysis.statistics.maximum_value_si)} {analysis.tag.si_unit}
          </dd>
        </div>
        <div>
          <dt>Cadence observée</dt>
          <dd>{formatInterval(analysis.observed_interval_seconds)}</dd>
        </div>
        <div>
          <dt>Qualités sélectionnées</dt>
          <dd>{analysis.included_qualities.map((quality) => SERIES_QUALITY_LABELS[quality]).join(", ") || "Aucune"}</dd>
        </div>
      </div>

      {analysis.issues.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Sévérité</th>
                <th>Occurrences</th>
                <th>Diagnostic</th>
              </tr>
            </thead>
            <tbody>
              {analysis.issues.map((issue) => (
                <tr key={issue.code}>
                  <td className="mono">{issue.code}</td>
                  <td><StatusBadge value={issue.severity} /></td>
                  <td>{formatNumber(issue.count, 0)}</td>
                  <td>{issue.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <SuccessNotice>Aucun diagnostic de qualité pour les filtres et seuils déclarés.</SuccessNotice>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Horodatage UTC</th>
              <th>Valeur SI</th>
              <th>Qualité</th>
              <th>Doublon</th>
              <th>Trou après</th>
              <th>Aberrant</th>
              <th>Séquence</th>
              <th>Source</th>
              <th>Dataset</th>
              <th>Ligne source</th>
              <th>Brut</th>
            </tr>
          </thead>
          <tbody>
            {analysis.items.map((point) => (
              <tr key={point.id}>
                <td>{formatDate(point.timestamp)}</td>
                <td>
                  {formatNumber(point.value_si)} {point.si_unit}
                </td>
                <td><StatusBadge value={point.quality} /></td>
                <td>{point.duplicate ? "Oui" : "—"}</td>
                <td>
                  {point.gap_after ? formatInterval(point.gap_after_seconds) : "—"}
                </td>
                <td>
                  {point.outlier
                    ? `Oui (${formatNumber(point.outlier_score ?? 0, 2)})`
                    : "—"}
                </td>
                <td>{point.sequence_number ?? "—"}</td>
                <td>{point.source_unit} · {String(point.source_value)}</td>
                <td className="mono hash">{point.dataset_id.slice(0, 12)}…</td>
                <td className="mono hash">{point.dataset_row_id?.slice(0, 12) ?? "—"}</td>
                <td className="mono hash">{point.raw_sample_id.slice(0, 12)}…</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="button-row">
        <button
          type="button"
          className="button button-secondary"
          disabled={analysis.offset === 0}
          onClick={onPreviousPage}
        >
          Points précédents
        </button>
        <span className="field-help">
          Points {formatNumber(pageStart, 0)}–{formatNumber(pageEnd, 0)} sur {formatNumber(analysis.total, 0)}
        </span>
        <button
          type="button"
          className="button button-secondary"
          disabled={analysis.offset + analysis.items.length >= analysis.total}
          onClick={onNextPage}
        >
          Points suivants
        </button>
      </div>
    </div>
  );
}

function SeriesMetric({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "green" | "blue" | "amber" | "purple";
}) {
  return (
    <article className={`metric-card ${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
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
