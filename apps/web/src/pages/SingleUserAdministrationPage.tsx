import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest, jsonBody } from "../api";
import {
  EmptyState,
  ErrorNotice,
  Panel,
  StatusBadge,
  SuccessNotice,
} from "../components/Shell";
import type {
  AuditEvent,
  Health,
  Organization,
  Page,
  RuleDefinition,
  RuleSet,
  StandardReference,
} from "../types";
import { formatDate } from "../types";

const METRICS = [
  "flow_m3_s",
  "min_pressure_pa",
  "max_pressure_pa",
  "total_head_loss_m",
  "total_power_w",
];

export function SingleUserAdministrationPage() {
  const queryClient = useQueryClient();
  const [organizationId, setOrganizationId] = useState("");
  const [selectedRuleSetId, setSelectedRuleSetId] = useState("");

  const [standardCode, setStandardCode] = useState("");
  const [standardTitle, setStandardTitle] = useState("");
  const [standardBody, setStandardBody] = useState("");
  const [standardEdition, setStandardEdition] = useState("");
  const [standardDate, setStandardDate] = useState("");
  const [standardCopyReference, setStandardCopyReference] = useState("");
  const [standardSourceUrl, setStandardSourceUrl] = useState("");

  const [ruleSetCode, setRuleSetCode] = useState("");
  const [ruleSetTitle, setRuleSetTitle] = useState("");
  const [ruleSetCountry, setRuleSetCountry] = useState("");
  const [ruleSetDomain, setRuleSetDomain] = useState("pipeline_liquide");
  const [ruleSetDescription, setRuleSetDescription] = useState("");
  const [ruleSetStandardIds, setRuleSetStandardIds] = useState<string[]>([]);

  const [ruleCode, setRuleCode] = useState("");
  const [ruleTitle, setRuleTitle] = useState("");
  const [ruleStandardId, setRuleStandardId] = useState("");
  const [ruleSeverity, setRuleSeverity] = useState<RuleDefinition["severity"]>("blocking");
  const [ruleMetric, setRuleMetric] = useState("max_pressure_pa");
  const [ruleOperator, setRuleOperator] = useState<RuleDefinition["operator"]>("le");
  const [ruleLimit, setRuleLimit] = useState("");
  const [ruleUpperLimit, setRuleUpperLimit] = useState("");
  const [ruleUnit, setRuleUnit] = useState("Pa");
  const [ruleMessage, setRuleMessage] = useState("");
  const [ruleClause, setRuleClause] = useState("");

  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<Page<Organization>>("/organizations?limit=20&offset=0"),
  });
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: () => apiRequest<Health>("/health"),
  });
  const standardsQuery = useQuery({
    queryKey: ["standards", organizationId],
    queryFn: () =>
      apiRequest<Page<StandardReference>>(
        "/standards?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });
  const ruleSetsQuery = useQuery({
    queryKey: ["rule-sets", organizationId],
    queryFn: () =>
      apiRequest<Page<RuleSet>>(
        "/rule-sets?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });
  const rulesQuery = useQuery({
    queryKey: ["rules", selectedRuleSetId],
    queryFn: () => apiRequest<RuleDefinition[]>("/rule-sets/" + selectedRuleSetId + "/rules"),
    enabled: Boolean(selectedRuleSetId),
  });
  const auditQuery = useQuery({
    queryKey: ["audit-events", organizationId],
    queryFn: () =>
      apiRequest<Page<AuditEvent>>(
        "/audit-events?limit=40&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });

  const organizations = organizationsQuery.data?.items ?? [];
  const standards = standardsQuery.data?.items ?? [];
  const activeStandards = standards.filter((standard) => standard.status === "active");
  const ruleSets = ruleSetsQuery.data?.items ?? [];
  const rules = rulesQuery.data ?? [];
  const auditEvents = auditQuery.data?.items ?? [];
  const selectedRuleSet = useMemo(
    () => ruleSets.find((ruleSet) => ruleSet.id === selectedRuleSetId),
    [ruleSets, selectedRuleSetId],
  );

  useEffect(() => {
    if (!organizationId && organizations.length) setOrganizationId(organizations[0].id);
  }, [organizationId, organizations]);

  useEffect(() => {
    if (!selectedRuleSetId || !ruleSets.some((item) => item.id === selectedRuleSetId)) {
      setSelectedRuleSetId(ruleSets[0]?.id ?? "");
    }
  }, [ruleSets, selectedRuleSetId]);

  useEffect(() => {
    setRuleSetStandardIds([]);
    setRuleStandardId("");
  }, [organizationId]);

  useEffect(() => {
    setRuleStandardId(selectedRuleSet?.standard_ids[0] ?? "");
  }, [selectedRuleSet]);

  const refreshAudit = () =>
    queryClient.invalidateQueries({ queryKey: ["audit-events", organizationId] });

  const standardMutation = useMutation({
    mutationFn: () =>
      apiRequest<StandardReference>("/standards", {
        method: "POST",
        body: jsonBody({
          organization_id: organizationId,
          code: standardCode,
          title: standardTitle,
          issuing_body: standardBody,
          edition: standardEdition,
          publication_date: standardDate || null,
          licensed_copy_ref: standardCopyReference || null,
          source_url: standardSourceUrl || null,
        }),
      }),
    onSuccess: async () => {
      setStandardCode("");
      setStandardTitle("");
      setStandardBody("");
      setStandardEdition("");
      setStandardDate("");
      setStandardCopyReference("");
      setStandardSourceUrl("");
      await queryClient.invalidateQueries({ queryKey: ["standards", organizationId] });
      await refreshAudit();
    },
  });

  const ruleSetMutation = useMutation({
    mutationFn: () =>
      apiRequest<RuleSet>("/rule-sets", {
        method: "POST",
        body: jsonBody({
          organization_id: organizationId,
          code: ruleSetCode,
          title: ruleSetTitle,
          country_code: ruleSetCountry || null,
          domain: ruleSetDomain,
          description: ruleSetDescription || null,
          standard_ids: ruleSetStandardIds,
        }),
      }),
    onSuccess: async (ruleSet) => {
      setRuleSetCode("");
      setRuleSetTitle("");
      setRuleSetCountry("");
      setRuleSetDescription("");
      setRuleSetStandardIds([]);
      setSelectedRuleSetId(ruleSet.id);
      await queryClient.invalidateQueries({ queryKey: ["rule-sets", organizationId] });
      await refreshAudit();
    },
  });

  const ruleMutation = useMutation({
    mutationFn: () =>
      apiRequest<RuleDefinition>("/rule-sets/" + selectedRuleSetId + "/rules", {
        method: "POST",
        body: jsonBody({
          standard_id: ruleStandardId || null,
          code: ruleCode,
          title: ruleTitle,
          severity: ruleSeverity,
          domain: "hydraulique",
          metric_path: ruleMetric,
          operator: ruleOperator,
          limit_value: Number(ruleLimit),
          upper_limit_value: ruleOperator === "between" ? Number(ruleUpperLimit) : null,
          unit: ruleUnit || null,
          applicability: { type: "always" },
          message: ruleMessage,
          source_clause_ref: ruleClause || null,
        }),
      }),
    onSuccess: async () => {
      setRuleCode("");
      setRuleTitle("");
      setRuleLimit("");
      setRuleUpperLimit("");
      setRuleMessage("");
      setRuleClause("");
      await queryClient.invalidateQueries({ queryKey: ["rules", selectedRuleSetId] });
      await queryClient.invalidateQueries({ queryKey: ["rule-sets", organizationId] });
      await refreshAudit();
    },
  });

  function toggleStandard(standardId: string): void {
    setRuleSetStandardIds((current) =>
      current.includes(standardId)
        ? current.filter((value) => value !== standardId)
        : [...current, standardId],
    );
  }

  const error =
    organizationsQuery.error ??
    healthQuery.error ??
    standardsQuery.error ??
    ruleSetsQuery.error ??
    rulesQuery.error ??
    auditQuery.error ??
    standardMutation.error ??
    ruleSetMutation.error ??
    ruleMutation.error;
  const success = standardMutation.isSuccess || ruleSetMutation.isSuccess || ruleMutation.isSuccess;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {success ? <SuccessNotice>La configuration a été enregistrée et rendue disponible.</SuccessNotice> : null}

      <Panel
        title="Instance mono-utilisateur"
        description="L'ingénieur connecté administre directement son espace PETROLE. Aucun rôle Approver ni seconde validation de compte n'est requis."
      >
        <div className="resource-summary">
          <div><span>Exploitant</span><strong>{organizations[0]?.name ?? "Non initialisé"}</strong></div>
          <div><span>Mode</span><strong>Ingénieur unique</strong></div>
          <div><span>Application</span><strong>v{healthQuery.data?.build?.application_version ?? "—"}</strong></div>
          <div><span>SHA Git</span><strong className="mono hash">{healthQuery.data?.build?.git_sha ?? "—"}</strong></div>
        </div>
      </Panel>

      <div className="content-grid equal">
        <Panel
          title="Références normatives"
          description="Enregistrez uniquement les éditions et sources que vous êtes autorisé à utiliser. Elles deviennent immédiatement disponibles dans l'espace mono-utilisateur."
        >
          <form className="compact-form" onSubmit={(event) => { event.preventDefault(); standardMutation.mutate(); }}>
            <div className="form-grid">
              <label>Code<input value={standardCode} onChange={(event) => setStandardCode(event.target.value.toUpperCase())} required /></label>
              <label>Édition<input value={standardEdition} onChange={(event) => setStandardEdition(event.target.value)} required /></label>
            </div>
            <label>Titre<input value={standardTitle} onChange={(event) => setStandardTitle(event.target.value)} required /></label>
            <label>Organisme émetteur<input value={standardBody} onChange={(event) => setStandardBody(event.target.value)} required /></label>
            <div className="form-grid">
              <label>Date de publication<input type="date" value={standardDate} onChange={(event) => setStandardDate(event.target.value)} /></label>
              <label>Référence de copie<input value={standardCopyReference} onChange={(event) => setStandardCopyReference(event.target.value)} /></label>
            </div>
            <label>URL source<input value={standardSourceUrl} onChange={(event) => setStandardSourceUrl(event.target.value)} /></label>
            <button className="button button-primary" disabled={!organizationId || standardMutation.isPending}>Enregistrer la référence</button>
          </form>

          {standards.length ? (
            <div className="table-wrap">
              <table><thead><tr><th>Référence</th><th>Édition</th><th>État</th></tr></thead><tbody>
                {standards.map((standard) => (
                  <tr key={standard.id}>
                    <td><strong>{standard.code}</strong><small>{standard.title}</small></td>
                    <td>{standard.edition}</td>
                    <td><StatusBadge value={standard.status === "active" ? "available" : standard.status} /></td>
                  </tr>
                ))}
              </tbody></table>
            </div>
          ) : <EmptyState title="Aucune référence" detail="Ajoutez la première référence normative ou interne." />}
        </Panel>

        <Panel
          title="Jeux de règles"
          description="Les règles sont enregistrées directement par l'ingénieur et deviennent utilisables sans étape d'approbation séparée."
        >
          <form className="compact-form" onSubmit={(event) => { event.preventDefault(); ruleSetMutation.mutate(); }}>
            <div className="form-grid">
              <label>Code<input value={ruleSetCode} onChange={(event) => setRuleSetCode(event.target.value.toUpperCase())} required /></label>
              <label>Pays<input value={ruleSetCountry} onChange={(event) => setRuleSetCountry(event.target.value.slice(0, 2).toUpperCase())} maxLength={2} /></label>
            </div>
            <label>Titre<input value={ruleSetTitle} onChange={(event) => setRuleSetTitle(event.target.value)} required /></label>
            <label>Domaine<input value={ruleSetDomain} onChange={(event) => setRuleSetDomain(event.target.value)} required /></label>
            <label>Description<textarea rows={2} value={ruleSetDescription} onChange={(event) => setRuleSetDescription(event.target.value)} /></label>
            <fieldset className="selection-fieldset">
              <legend>Références associées</legend>
              {activeStandards.map((standard) => (
                <label className="selection-option" key={standard.id}>
                  <input type="checkbox" checked={ruleSetStandardIds.includes(standard.id)} onChange={() => toggleStandard(standard.id)} />
                  <span><strong>{standard.code}</strong><small>{standard.title}</small></span>
                </label>
              ))}
            </fieldset>
            <button className="button button-primary" disabled={!organizationId || !ruleSetStandardIds.length || ruleSetMutation.isPending}>Créer le jeu</button>
          </form>

          {ruleSets.length ? (
            <label>
              Jeu à éditer
              <select value={selectedRuleSetId} onChange={(event) => setSelectedRuleSetId(event.target.value)}>
                {ruleSets.map((ruleSet) => <option key={ruleSet.id} value={ruleSet.id}>{ruleSet.code} — {ruleSet.title}</option>)}
              </select>
            </label>
          ) : null}
        </Panel>
      </div>

      <Panel
        title="Règles du jeu sélectionné"
        description="Ajoutez autant de contrôles que nécessaire. Le système conserve les empreintes et la traçabilité automatiquement."
      >
        {selectedRuleSet ? (
          <>
            <form className="editor-form" onSubmit={(event) => { event.preventDefault(); ruleMutation.mutate(); }}>
              <div className="form-grid three">
                <label>Code<input value={ruleCode} onChange={(event) => setRuleCode(event.target.value.toUpperCase())} required /></label>
                <label>Métrique<select value={ruleMetric} onChange={(event) => setRuleMetric(event.target.value)}>{METRICS.map((metric) => <option key={metric} value={metric}>{metric}</option>)}</select></label>
                <label>Sévérité<select value={ruleSeverity} onChange={(event) => setRuleSeverity(event.target.value as RuleDefinition["severity"])}><option value="information">Information</option><option value="warning">Avertissement</option><option value="error">Erreur</option><option value="blocking">Bloquant</option></select></label>
              </div>
              <label>Titre<input value={ruleTitle} onChange={(event) => setRuleTitle(event.target.value)} required /></label>
              <div className="form-grid three">
                <label>Opérateur<select value={ruleOperator} onChange={(event) => setRuleOperator(event.target.value as RuleDefinition["operator"])}><option value="le">≤</option><option value="lt">&lt;</option><option value="ge">≥</option><option value="gt">&gt;</option><option value="eq">=</option><option value="between">Intervalle</option></select></label>
                <label>Limite<input type="number" step="any" value={ruleLimit} onChange={(event) => setRuleLimit(event.target.value)} required /></label>
                {ruleOperator === "between" ? <label>Limite haute<input type="number" step="any" value={ruleUpperLimit} onChange={(event) => setRuleUpperLimit(event.target.value)} required /></label> : <label>Unité<input value={ruleUnit} onChange={(event) => setRuleUnit(event.target.value)} /></label>}
              </div>
              <label>Référence normative<select value={ruleStandardId} onChange={(event) => setRuleStandardId(event.target.value)}><option value="">Aucune</option>{standards.filter((standard) => selectedRuleSet.standard_ids.includes(standard.id)).map((standard) => <option key={standard.id} value={standard.id}>{standard.code}</option>)}</select></label>
              <label>Message<input value={ruleMessage} onChange={(event) => setRuleMessage(event.target.value)} required /></label>
              <label>Clause/source<input value={ruleClause} onChange={(event) => setRuleClause(event.target.value)} /></label>
              <button className="button button-primary" disabled={ruleMutation.isPending}>Ajouter la règle</button>
            </form>

            {rules.length ? (
              <div className="table-wrap">
                <table><thead><tr><th>Règle</th><th>Métrique</th><th>Limite</th><th>État</th></tr></thead><tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id}>
                      <td><strong>{rule.code}</strong><small>{rule.title}</small></td>
                      <td>{rule.metric_path}</td>
                      <td>{rule.operator} {rule.limit_value} {rule.unit ?? ""}</td>
                      <td><StatusBadge value={rule.status === "archived" ? "archived" : "available"} /></td>
                    </tr>
                  ))}
                </tbody></table>
              </div>
            ) : <EmptyState title="Aucune règle" detail="Ajoutez le premier contrôle de ce jeu." />}
          </>
        ) : <EmptyState title="Aucun jeu sélectionné" detail="Créez ou sélectionnez un jeu de règles." />}
      </Panel>

      <Panel title="Journal d'audit" description="Traçabilité des dernières opérations réalisées dans l'espace de l'ingénieur.">
        {auditEvents.length ? (
          <div className="table-wrap">
            <table><thead><tr><th>Date</th><th>Action</th><th>Objet</th></tr></thead><tbody>
              {auditEvents.map((event) => <tr key={event.id}><td>{formatDate(event.created_at)}</td><td>{event.action}</td><td className="mono">{event.object_type} · {event.object_id.slice(0, 8)}</td></tr>)}
            </tbody></table>
          </div>
        ) : <EmptyState title="Journal vide" detail="Les opérations apparaîtront ici." />}
      </Panel>
    </div>
  );
}
