import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { apiRequest, downloadApiFile, jsonBody } from "../api";
import { EmptyState, ErrorNotice, Panel, StatusBadge, SuccessNotice } from "../components/Shell";
import type {
  Calculation,
  CalculationResult,
  Comparison,
  ModelVersion,
  Page,
  Project,
  Report,
  Scenario,
  Transfer,
} from "../types";
import { formatDate } from "../types";

export function RapportsPage() {
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [calculationId, setCalculationId] = useState("");
  const [calculation, setCalculation] = useState<Calculation | null>(null);
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [hydraulicReport, setHydraulicReport] = useState<Report | null>(null);
  const [operationalReport, setOperationalReport] = useState<Report | null>(null);
  const [comment, setComment] = useState("");
  const [operationalType, setOperationalType] = useState("project_sheet");
  const [sourceId, setSourceId] = useState("");

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiRequest<Page<Project>>("/projects?limit=200&offset=0"),
  });
  const modelsQuery = useQuery({
    queryKey: ["models", projectId],
    queryFn: () =>
      apiRequest<Page<ModelVersion>>("/projects/" + projectId + "/models?limit=200&offset=0"),
    enabled: Boolean(projectId),
  });
  const scenariosQuery = useQuery({
    queryKey: ["scenarios", modelId],
    queryFn: () =>
      apiRequest<Page<Scenario>>("/models/" + modelId + "/scenarios?limit=200&offset=0"),
    enabled: Boolean(modelId),
  });
  const calculationsQuery = useQuery({
    queryKey: ["calculations", scenarioId],
    queryFn: () =>
      apiRequest<Page<Calculation>>(
        "/scenarios/" + scenarioId + "/calculations?limit=200&offset=0",
      ),
    enabled: Boolean(scenarioId),
  });

  const projects = projectsQuery.data?.items ?? [];
  const organizationId =
    projects.find((project) => project.id === projectId)?.organization_id ?? "";
  const models = modelsQuery.data?.items ?? [];
  const scenarios = scenariosQuery.data?.items ?? [];
  const calculations = calculationsQuery.data?.items ?? [];

  useEffect(() => {
    if (!projects.some((project) => project.id === projectId)) {
      setProjectId(projects[0]?.id ?? "");
    }
  }, [projectId, projects]);

  useEffect(() => {
    if (!models.some((model) => model.id === modelId)) {
      setModelId(models[0]?.id ?? "");
    }
  }, [modelId, models]);

  useEffect(() => {
    if (!scenarios.some((scenario) => scenario.id === scenarioId)) {
      setScenarioId(scenarios[0]?.id ?? "");
    }
  }, [scenarioId, scenarios]);

  useEffect(() => {
    if (!calculations.some((item) => item.id === calculationId)) {
      setCalculationId(calculations[0]?.id ?? "");
    }
  }, [calculationId, calculations]);

  const comparisonsQuery = useQuery({
    queryKey: ["comparisons", projectId],
    queryFn: () =>
      apiRequest<Page<Comparison>>("/projects/" + projectId + "/comparisons?limit=200&offset=0"),
    enabled: Boolean(projectId) && operationalType === "scenario_comparison",
  });
  const transfersQuery = useQuery({
    queryKey: ["transfers", organizationId],
    queryFn: () =>
      apiRequest<Page<Transfer>>(
        "/organizations/" + organizationId + "/transfers?limit=200&offset=0",
      ),
    enabled:
      Boolean(organizationId) &&
      (operationalType === "transfer_simulation" || operationalType === "material_balance"),
  });

  const lookupMutation = useMutation({
    mutationFn: async () => {
      const selectedCalculation = await apiRequest<Calculation>("/calculations/" + calculationId);
      const selectedResult = await apiRequest<CalculationResult>(
        "/calculations/" + selectedCalculation.id + "/results",
      );
      return { calculation: selectedCalculation, result: selectedResult };
    },
    onSuccess: (value) => {
      setCalculation(value.calculation);
      setCalculationResult(value.result);
      setHydraulicReport(null);
    },
  });

  const reportMutation = useMutation({
    mutationFn: () =>
      apiRequest<Report>("/calculations/" + calculation?.id + "/reports", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: jsonBody({
          report_type: "hydraulic_calculation",
          template_version: "rpt-02/1.0",
          format: "pdf",
          locale: "fr",
        }),
      }),
    onSuccess: setHydraulicReport,
  });

  const operationalMutation = useMutation({
    mutationFn: () =>
      apiRequest<Report>("/reports", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: jsonBody({ report_type: operationalType, source_id: sourceId.trim() }),
      }),
    onSuccess: setOperationalReport,
  });
  const downloadMutation = useMutation({
    mutationFn: (target: Report) =>
      downloadApiFile(
        "/reports/" + target.id + "/download",
        "rapport-" + target.report_type + "-" + target.id.slice(0, 8) + ".pdf",
      ),
  });
  const approvalMutation = useMutation({
    mutationFn: (decision: "approved" | "rejected") =>
      apiRequest<Report>("/reports/" + hydraulicReport?.id + "/approve", {
        method: "POST",
        body: jsonBody({ decision, comment: comment || null }),
      }),
    onSuccess: setHydraulicReport,
  });

  const sourceOptions = buildSourceOptions(operationalType, {
    projects,
    calculations,
    comparisons: comparisonsQuery.data?.items ?? [],
    transfers: transfersQuery.data?.items ?? [],
  });

  useEffect(() => {
    if (!sourceOptions.some((option) => option.id === sourceId)) {
      setSourceId(sourceOptions[0]?.id ?? "");
    }
  }, [sourceId, sourceOptions]);

  const error =
    projectsQuery.error ??
    comparisonsQuery.error ??
    transfersQuery.error ??
    modelsQuery.error ??
    scenariosQuery.error ??
    calculationsQuery.error ??
    lookupMutation.error ??
    reportMutation.error ??
    operationalMutation.error ??
    approvalMutation.error ??
    downloadMutation.error;
  const decisionEligible = calculationResult?.result?.decision_eligible === true;
  const complianceStatus =
    calculationResult?.result?.compliance_status ?? "not_evaluated";

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {approvalMutation.isSuccess ? (
        <SuccessNotice>La décision a été enregistrée dans le journal d'audit.</SuccessNotice>
      ) : null}

      <Panel
        title="Calcul source"
        description="Un rapport est toujours rattaché à une exécution immuable."
      >
        <form
          className="lookup-form"
          onSubmit={(event) => {
            event.preventDefault();
            lookupMutation.mutate();
          }}
        >
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
            Version de modèle
            <select
              value={modelId}
              onChange={(event) => setModelId(event.target.value)}
              disabled={!projectId}
            >
              <option value="">Sélectionner</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  V{model.version_number} — {model.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Scénario
            <select
              value={scenarioId}
              onChange={(event) => setScenarioId(event.target.value)}
              disabled={!modelId}
            >
              <option value="">Sélectionner</option>
              {scenarios.map((scenario) => (
                <option key={scenario.id} value={scenario.id}>
                  {scenario.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Calcul
            <select
              value={calculationId}
              onChange={(event) => setCalculationId(event.target.value)}
              disabled={!scenarioId}
            >
              <option value="">Sélectionner</option>
              {calculations.map((item) => (
                <option key={item.id} value={item.id}>
                  {formatDate(item.created_at)} — {item.status} ({item.id.slice(0, 8)})
                </option>
              ))}
            </select>
          </label>
          <button
            className="button button-secondary"
            disabled={!calculationId || lookupMutation.isPending}
          >
            Vérifier
          </button>
        </form>

        {calculation ? (
          <div className="resource-summary">
            <div>
              <span>Statut du calcul</span>
              <StatusBadge value={calculation.status} />
            </div>
            <div>
              <span>Moteur</span>
              <strong>{calculation.engine_version}</strong>
            </div>
            <div>
              <span>Empreinte d'entrée</span>
              <strong className="mono hash">{calculation.input_hash}</strong>
            </div>
            <div>
              <span>Conformité</span>
              <StatusBadge value={complianceStatus} />
            </div>
            <div>
              <span>Décision positive</span>
              <StatusBadge value={decisionEligible ? "éligible" : "interdite"} />
            </div>
          </div>
        ) : null}
      </Panel>

      <Panel
        title="Note de calcul hydraulique"
        description="PDF A4 en français, entrées, méthode, KPI, profils, contrôles et traçabilité."
      >
        {calculation ? (
          <div className="report-workflow">
            <div className="report-preview">
              <span className="document-icon" aria-hidden="true">
                PDF
              </span>
              <div>
                <h3>RPT-02 — Note de calcul hydraulique</h3>
                <p>Modèle rpt-02/1.0 · langue française</p>
              </div>
              <button
                className="button button-primary"
                disabled={reportMutation.isPending}
                onClick={() => reportMutation.mutate()}
              >
                {reportMutation.isPending ? "Génération…" : "Générer et archiver"}
              </button>
            </div>

            {hydraulicReport ? (
              <div className="report-result">
                <dl className="detail-list">
                  <div>
                    <dt>Statut</dt>
                    <dd>
                      <StatusBadge value={hydraulicReport.status} />
                    </dd>
                  </div>
                  <div>
                    <dt>Création</dt>
                    <dd>{formatDate(hydraulicReport.created_at)}</dd>
                  </div>
                  <div>
                    <dt>Empreinte PDF</dt>
                    <dd className="mono hash">{hydraulicReport.content_hash}</dd>
                  </div>
                  <div>
                    <dt>Modèle</dt>
                    <dd>{hydraulicReport.template_version}</dd>
                  </div>
                </dl>

                <div className="button-row">
                  <button
                    className="button button-secondary"
                    disabled={downloadMutation.isPending}
                    onClick={() => downloadMutation.mutate(hydraulicReport)}
                  >
                    {downloadMutation.isPending ? "Téléchargement…" : "Télécharger le PDF"}
                  </button>
                </div>

                {hydraulicReport.status === "generated" ? (
                  <div className="approval-box">
                    {!decisionEligible ? (
                      <div className="notice notice-error" role="alert">
                        Approbation positive interdite : conformité {complianceStatus}.
                        Le rejet reste disponible et traçable.
                      </div>
                    ) : null}
                    <label>
                      Commentaire de décision
                      <textarea
                        rows={3}
                        value={comment}
                        onChange={(event) => setComment(event.target.value)}
                        placeholder="Contrôles effectués, réserves ou motif du rejet."
                      />
                    </label>
                    <div className="button-row">
                      <button
                        className="button button-primary"
                        disabled={approvalMutation.isPending || !decisionEligible}
                        onClick={() => approvalMutation.mutate("approved")}
                      >
                        Approuver
                      </button>
                      <button
                        className="button button-danger"
                        disabled={approvalMutation.isPending}
                        onClick={() => approvalMutation.mutate("rejected")}
                      >
                        Rejeter
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="notice">
                    Décision enregistrée le {formatDate(hydraulicReport.approved_at)}.
                    {hydraulicReport.approval_comment ? " Commentaire : " + hydraulicReport.approval_comment : ""}
                  </div>
                )}
              </div>
            ) : (
              <EmptyState
                title="Rapport non généré"
                detail="La génération utilise le résultat figé du calcul sélectionné."
              />
            )}
          </div>
        ) : (
          <EmptyState
            title="Calcul requis"
            detail="Saisissez l'identifiant d'un calcul convergé pour préparer son rapport."
          />
        )}
      </Panel>

      <Panel
        title="Rapports opérationnels"
        description="RPT-01 projet, RPT-03 comparaison, RPT-04 stations, RPT-05 transfert et RPT-06 bilan."
      >
        <form
          className="lookup-form"
          onSubmit={(event) => {
            event.preventDefault();
            operationalMutation.mutate();
          }}
        >
          <label>
            Modèle de rapport
            <select value={operationalType} onChange={(event) => setOperationalType(event.target.value)}>
              <option value="project_sheet">RPT-01 — Fiche projet</option>
              <option value="scenario_comparison">RPT-03 — Comparaison</option>
              <option value="station_pumps">RPT-04 — Stations et pompes</option>
              <option value="transfer_simulation">RPT-05 — Transfert</option>
              <option value="material_balance">RPT-06 — Bilan matière</option>
            </select>
          </label>
          <label>
            {SOURCE_LABELS[operationalType] ?? "Source"}
            <select
              value={sourceId}
              onChange={(event) => setSourceId(event.target.value)}
              required
            >
              <option value="">Sélectionner</option>
              {sourceOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
            {sourceOptions.length ? null : (
              <small>Aucune source disponible pour ce modèle de rapport.</small>
            )}
          </label>
          <button className="button button-primary" disabled={operationalMutation.isPending}>
            {operationalMutation.isPending ? "Génération…" : "Générer et archiver"}
          </button>
        </form>
        {operationalMutation.isSuccess && operationalReport ? (
          <div className="notice notice-success">
            {operationalReport.template_version} généré · empreinte <span className="mono">{operationalReport.content_hash.slice(0, 24)}…</span>
            <button className="button button-secondary" onClick={() => downloadMutation.mutate(operationalReport)}>
              Télécharger
            </button>
          </div>
        ) : null}
      </Panel>
      <Panel
        title="Garanties du document"
        description="Contrôles intégrés au processus de production."
      >
        <div className="guarantee-grid">
          <Guarantee title="Immuable" detail="Le binaire est haché avant archivage." />
          <Guarantee title="Reproductible" detail="Entrées et version moteur sont incluses." />
          <Guarantee title="Lisible" detail="Unités SI, graphiques et messages en français." />
          <Guarantee title="Approuvable" detail="Décision humaine irréversible et auditée." />
        </div>
      </Panel>
    </div>
  );
}

function Guarantee({ title, detail }: { title: string; detail: string }) {
  return (
    <article>
      <span aria-hidden="true">✓</span>
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
    </article>
  );
}

/** Intitulé du sélecteur de source, par modèle de rapport. */
const SOURCE_LABELS: Record<string, string> = {
  project_sheet: "Projet",
  scenario_comparison: "Comparaison",
  station_pumps: "Calcul",
  transfer_simulation: "Transfert",
  material_balance: "Transfert",
};

interface SourceOption {
  id: string;
  label: string;
}

/** Associe chaque modèle de rapport aux ressources réellement acceptées par l'API. */
export function buildSourceOptions(
  reportType: string,
  data: {
    projects: Project[];
    calculations: Calculation[];
    comparisons: Comparison[];
    transfers: Transfer[];
  },
): SourceOption[] {
  if (reportType === "project_sheet") {
    return data.projects.map((project) => ({
      id: project.id,
      label: project.code + " — " + project.name,
    }));
  }
  if (reportType === "scenario_comparison") {
    return data.comparisons.map((comparison) => ({
      id: comparison.id,
      label:
        formatDate(comparison.created_at) +
        " — " +
        String(comparison.calculation_ids.length) +
        " calculs",
    }));
  }
  if (reportType === "station_pumps") {
    return data.calculations.map((calculation) => ({
      id: calculation.id,
      label: formatDate(calculation.created_at) + " — " + calculation.status,
    }));
  }
  return data.transfers.map((transfer) => ({
    id: transfer.id,
    label: formatDate(transfer.created_at) + " — " + transfer.status,
  }));
}
