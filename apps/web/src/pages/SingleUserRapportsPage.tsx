import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { apiRequest, downloadApiFile, jsonBody } from "../api";
import { EmptyState, ErrorNotice, Panel, StatusBadge, SuccessNotice } from "../components/Shell";
import type {
  Calculation,
  Comparison,
  ModelVersion,
  Page,
  Project,
  Report,
  Scenario,
  Transfer,
} from "../types";
import { formatDate } from "../types";

export function SingleUserRapportsPage() {
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [calculationId, setCalculationId] = useState("");
  const [hydraulicReport, setHydraulicReport] = useState<Report | null>(null);
  const [operationalReport, setOperationalReport] = useState<Report | null>(null);
  const [operationalType, setOperationalType] = useState("project_sheet");
  const [sourceId, setSourceId] = useState("");

  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: () => apiRequest<Page<Project>>("/projects?limit=200&offset=0") });
  const modelsQuery = useQuery({
    queryKey: ["models", projectId],
    queryFn: () => apiRequest<Page<ModelVersion>>("/projects/" + projectId + "/models?limit=200&offset=0"),
    enabled: Boolean(projectId),
  });
  const scenariosQuery = useQuery({
    queryKey: ["scenarios", modelId],
    queryFn: () => apiRequest<Page<Scenario>>("/models/" + modelId + "/scenarios?limit=200&offset=0"),
    enabled: Boolean(modelId),
  });
  const calculationsQuery = useQuery({
    queryKey: ["calculations", scenarioId],
    queryFn: () => apiRequest<Page<Calculation>>("/scenarios/" + scenarioId + "/calculations?limit=200&offset=0"),
    enabled: Boolean(scenarioId),
  });

  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];
  const scenarios = scenariosQuery.data?.items ?? [];
  const calculations = calculationsQuery.data?.items ?? [];
  const organizationId = projects.find((project) => project.id === projectId)?.organization_id ?? "";

  useEffect(() => {
    if (!projects.some((project) => project.id === projectId)) setProjectId(projects[0]?.id ?? "");
  }, [projectId, projects]);
  useEffect(() => {
    if (!models.some((model) => model.id === modelId)) setModelId(models[0]?.id ?? "");
  }, [modelId, models]);
  useEffect(() => {
    if (!scenarios.some((scenario) => scenario.id === scenarioId)) setScenarioId(scenarios[0]?.id ?? "");
  }, [scenarioId, scenarios]);
  useEffect(() => {
    if (!calculations.some((calculation) => calculation.id === calculationId)) setCalculationId(calculations[0]?.id ?? "");
  }, [calculationId, calculations]);

  const comparisonsQuery = useQuery({
    queryKey: ["comparisons", projectId],
    queryFn: () => apiRequest<Page<Comparison>>("/projects/" + projectId + "/comparisons?limit=200&offset=0"),
    enabled: Boolean(projectId) && operationalType === "scenario_comparison",
  });
  const transfersQuery = useQuery({
    queryKey: ["transfers", organizationId],
    queryFn: () => apiRequest<Page<Transfer>>("/organizations/" + organizationId + "/transfers?limit=200&offset=0"),
    enabled: Boolean(organizationId) && (operationalType === "transfer_simulation" || operationalType === "material_balance"),
  });

  const hydraulicMutation = useMutation({
    mutationFn: () => apiRequest<Report>("/calculations/" + calculationId + "/reports", {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: jsonBody({ report_type: "hydraulic_calculation", template_version: "rpt-02/1.0", format: "pdf", locale: "fr" }),
    }),
    onSuccess: setHydraulicReport,
  });

  const operationalMutation = useMutation({
    mutationFn: () => apiRequest<Report>("/reports", {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: jsonBody({ report_type: operationalType, source_id: sourceId }),
    }),
    onSuccess: setOperationalReport,
  });

  const downloadMutation = useMutation({
    mutationFn: (report: Report) => downloadApiFile(
      "/reports/" + report.id + "/download",
      "rapport-" + report.report_type + "-" + report.id.slice(0, 8) + ".pdf",
    ),
  });

  const sourceOptions = useMemo(() => {
    if (operationalType === "project_sheet") {
      return projects.map((project) => ({ id: project.id, label: project.code + " — " + project.name }));
    }
    if (operationalType === "station_pumps") {
      return calculations.map((calculation) => ({ id: calculation.id, label: formatDate(calculation.created_at) + " — " + calculation.status }));
    }
    if (operationalType === "scenario_comparison") {
      return (comparisonsQuery.data?.items ?? []).map((comparison) => ({ id: comparison.id, label: "Comparaison " + comparison.id.slice(0, 8) }));
    }
    return (transfersQuery.data?.items ?? []).map((transfer) => ({ id: transfer.id, label: "Transfert " + transfer.id.slice(0, 8) + " — " + transfer.status }));
  }, [operationalType, projects, calculations, comparisonsQuery.data, transfersQuery.data]);

  useEffect(() => {
    if (!sourceOptions.some((option) => option.id === sourceId)) setSourceId(sourceOptions[0]?.id ?? "");
  }, [sourceId, sourceOptions]);

  const selectedCalculation = calculations.find((calculation) => calculation.id === calculationId);
  const error = projectsQuery.error ?? modelsQuery.error ?? scenariosQuery.error ?? calculationsQuery.error ?? comparisonsQuery.error ?? transfersQuery.error ?? hydraulicMutation.error ?? operationalMutation.error ?? downloadMutation.error;
  const success = hydraulicMutation.isSuccess || operationalMutation.isSuccess;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {success ? <SuccessNotice>Le rapport a été généré, haché et archivé.</SuccessNotice> : null}

      <Panel
        title="Note de calcul hydraulique"
        description="L'ingénieur génère directement le document depuis un calcul archivé. Aucun workflow d'approbation ou de rejet séparé n'est requis."
      >
        <div className="form-grid four">
          <label>Projet<select value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Sélectionner</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.code} — {project.name}</option>)}</select></label>
          <label>Version<select value={modelId} onChange={(event) => setModelId(event.target.value)} disabled={!projectId}><option value="">Sélectionner</option>{models.map((model) => <option key={model.id} value={model.id}>V{model.version_number} — {model.name}</option>)}</select></label>
          <label>Scénario<select value={scenarioId} onChange={(event) => setScenarioId(event.target.value)} disabled={!modelId}><option value="">Sélectionner</option>{scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name}</option>)}</select></label>
          <label>Calcul<select value={calculationId} onChange={(event) => setCalculationId(event.target.value)} disabled={!scenarioId}><option value="">Sélectionner</option>{calculations.map((calculation) => <option key={calculation.id} value={calculation.id}>{formatDate(calculation.created_at)} — {calculation.status}</option>)}</select></label>
        </div>

        {selectedCalculation ? (
          <div className="resource-summary">
            <div><span>Statut</span><StatusBadge value={selectedCalculation.status} /></div>
            <div><span>Moteur</span><strong>{selectedCalculation.engine_version}</strong></div>
            <div><span>Empreinte</span><strong className="mono hash">{selectedCalculation.input_hash}</strong></div>
          </div>
        ) : null}

        <div className="button-row">
          <button className="button button-primary" disabled={!calculationId || hydraulicMutation.isPending} onClick={() => hydraulicMutation.mutate()}>
            {hydraulicMutation.isPending ? "Génération…" : "Générer et archiver la note"}
          </button>
        </div>

        {hydraulicReport ? <ReportCard report={hydraulicReport} onDownload={() => downloadMutation.mutate(hydraulicReport)} downloading={downloadMutation.isPending} /> : <EmptyState title="Aucune note générée" detail="Sélectionnez un calcul puis générez sa note de calcul." />}
      </Panel>

      <Panel
        title="Rapports opérationnels"
        description="RPT-01 projet, RPT-03 comparaison, RPT-04 stations, RPT-05 transfert et RPT-06 bilan matière."
      >
        <form className="lookup-form" onSubmit={(event) => { event.preventDefault(); operationalMutation.mutate(); }}>
          <label>
            Modèle de rapport
            <select value={operationalType} onChange={(event) => setOperationalType(event.target.value)}>
              <option value="project_sheet">RPT-01 — Fiche projet</option>
              <option value="scenario_comparison">RPT-03 — Comparaison de scénarios</option>
              <option value="station_pumps">RPT-04 — Stations et pompes</option>
              <option value="transfer_simulation">RPT-05 — Transfert</option>
              <option value="material_balance">RPT-06 — Bilan matière</option>
            </select>
          </label>
          <label>
            Source
            <select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
              <option value="">Sélectionner</option>
              {sourceOptions.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
            </select>
          </label>
          <button className="button button-primary" disabled={!sourceId || operationalMutation.isPending}>Générer et archiver</button>
        </form>

        {operationalReport ? <ReportCard report={operationalReport} onDownload={() => downloadMutation.mutate(operationalReport)} downloading={downloadMutation.isPending} /> : <EmptyState title="Aucun rapport opérationnel" detail="Choisissez un modèle et sa source." />}
      </Panel>
    </div>
  );
}

function ReportCard({ report, onDownload, downloading }: { report: Report; onDownload: () => void; downloading: boolean }) {
  return (
    <div className="report-result">
      <dl className="detail-list">
        <div><dt>Type</dt><dd>{report.report_type}</dd></div>
        <div><dt>Création</dt><dd>{formatDate(report.created_at)}</dd></div>
        <div><dt>État</dt><dd><StatusBadge value="generated" /></dd></div>
        <div><dt>Empreinte</dt><dd className="mono hash">{report.content_hash}</dd></div>
      </dl>
      <div className="button-row"><button className="button button-secondary" disabled={downloading} onClick={onDownload}>{downloading ? "Téléchargement…" : "Télécharger le PDF"}</button></div>
    </div>
  );
}
