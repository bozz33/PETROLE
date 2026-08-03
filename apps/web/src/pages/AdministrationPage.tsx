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
  Organization,
  OrganizationMember,
  OrganizationRole,
  Page,
  RuleDefinition,
  RuleSet,
  StandardReference,
} from "../types";
import { formatDate } from "../types";

const ROLES: Array<{ value: OrganizationRole; label: string }> = [
  { value: "admin", label: "Administrateur" },
  { value: "engineer", label: "Ingénieur calcul" },
  { value: "operator", label: "Exploitant" },
  { value: "approver", label: "Approbateur" },
  { value: "viewer", label: "Lecteur" },
];

const METRICS = [
  "flow_m3_s",
  "min_pressure_pa",
  "max_pressure_pa",
  "total_head_loss_m",
  "total_power_w",
];

export function AdministrationPage() {
  const queryClient = useQueryClient();
  const [organizationId, setOrganizationId] = useState("");
  const [selectedRuleSetId, setSelectedRuleSetId] = useState("");

  const [memberEmail, setMemberEmail] = useState("");
  const [memberName, setMemberName] = useState("");
  const [memberPassword, setMemberPassword] = useState("");
  const [memberRole, setMemberRole] = useState<OrganizationRole>("engineer");

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
  const [ruleSeverity, setRuleSeverity] =
    useState<RuleDefinition["severity"]>("blocking");
  const [ruleMetric, setRuleMetric] = useState("max_pressure_pa");
  const [ruleOperator, setRuleOperator] =
    useState<RuleDefinition["operator"]>("le");
  const [ruleLimit, setRuleLimit] = useState("");
  const [ruleUpperLimit, setRuleUpperLimit] = useState("");
  const [ruleUnit, setRuleUnit] = useState("Pa");
  const [ruleMessage, setRuleMessage] = useState("");
  const [ruleClause, setRuleClause] = useState("");

  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<Page<Organization>>("/organizations?limit=200&offset=0"),
  });
  const membersQuery = useQuery({
    queryKey: ["members", organizationId],
    queryFn: () =>
      apiRequest<OrganizationMember[]>(
        "/organizations/" + organizationId + "/members",
      ),
    enabled: Boolean(organizationId),
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
    queryFn: () =>
      apiRequest<RuleDefinition[]>(
        "/rule-sets/" + selectedRuleSetId + "/rules",
      ),
    enabled: Boolean(selectedRuleSetId),
  });
  const auditQuery = useQuery({
    queryKey: ["audit-events", organizationId],
    queryFn: () =>
      apiRequest<Page<AuditEvent>>(
        "/audit-events?limit=30&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });

  const organizations = organizationsQuery.data?.items ?? [];
  const members = membersQuery.data ?? [];
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
    if (!organizationId && organizations.length) {
      setOrganizationId(organizations[0].id);
    }
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
    if (selectedRuleSet?.standard_ids.length) {
      setRuleStandardId(selectedRuleSet.standard_ids[0]);
    } else {
      setRuleStandardId("");
    }
  }, [selectedRuleSet]);

  const refreshAudit = () =>
    queryClient.invalidateQueries({ queryKey: ["audit-events", organizationId] });

  const memberMutation = useMutation({
    mutationFn: () =>
      apiRequest<OrganizationMember>(
        "/organizations/" + organizationId + "/members",
        {
          method: "POST",
          body: jsonBody({
            email: memberEmail,
            full_name: memberName,
            password: memberPassword,
            role: memberRole,
          }),
        },
      ),
    onSuccess: async () => {
      setMemberEmail("");
      setMemberName("");
      setMemberPassword("");
      await queryClient.invalidateQueries({ queryKey: ["members", organizationId] });
      await refreshAudit();
    },
  });

  const memberRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: OrganizationRole }) =>
      apiRequest<OrganizationMember>(
        "/organizations/" + organizationId + "/members/" + userId,
        { method: "PATCH", body: jsonBody({ role }) },
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["members", organizationId] });
      await refreshAudit();
    },
  });

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

  const approveStandardMutation = useMutation({
    mutationFn: (standardId: string) =>
      apiRequest<StandardReference>("/standards/" + standardId + "/approve", {
        method: "POST",
      }),
    onSuccess: async () => {
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
          upper_limit_value:
            ruleOperator === "between" ? Number(ruleUpperLimit) : null,
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

  const approveRuleMutation = useMutation({
    mutationFn: (ruleId: string) =>
      apiRequest<RuleDefinition>("/rules/" + ruleId + "/approve", {
        method: "POST",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["rules", selectedRuleSetId] });
      await queryClient.invalidateQueries({ queryKey: ["rule-sets", organizationId] });
      await refreshAudit();
    },
  });

  const approveRuleSetMutation = useMutation({
    mutationFn: () =>
      apiRequest<RuleSet>("/rule-sets/" + selectedRuleSetId + "/approve", {
        method: "POST",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["rule-sets", organizationId] });
      await queryClient.invalidateQueries({
        queryKey: ["rule-sets", organizationId, "approved"],
      });
      await refreshAudit();
    },
  });

  const toggleStandard = (standardId: string) => {
    setRuleSetStandardIds(
      ruleSetStandardIds.includes(standardId)
        ? ruleSetStandardIds.filter((value) => value !== standardId)
        : [...ruleSetStandardIds, standardId],
    );
  };

  const error =
    organizationsQuery.error ??
    membersQuery.error ??
    standardsQuery.error ??
    ruleSetsQuery.error ??
    rulesQuery.error ??
    auditQuery.error ??
    memberMutation.error ??
    memberRoleMutation.error ??
    standardMutation.error ??
    approveStandardMutation.error ??
    ruleSetMutation.error ??
    ruleMutation.error ??
    approveRuleMutation.error ??
    approveRuleSetMutation.error;
  const success =
    memberMutation.isSuccess ||
    memberRoleMutation.isSuccess ||
    standardMutation.isSuccess ||
    approveStandardMutation.isSuccess ||
    ruleSetMutation.isSuccess ||
    ruleMutation.isSuccess ||
    approveRuleMutation.isSuccess ||
    approveRuleSetMutation.isSuccess;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {success ? (
        <SuccessNotice>La décision a été enregistrée dans le journal d'audit.</SuccessNotice>
      ) : null}

      <Panel
        title="Périmètre administratif"
        description="Toutes les opérations ci-dessous restent isolées dans l'organisation choisie."
      >
        <label className="single-field">
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
      </Panel>

      <div className="content-grid equal">
        <Panel title="Membres et rôles" description="Comptes autorisés dans l'organisation.">
          {members.length ? (
            <div className="card-list">
              {members.map((member) => (
                <article className="compact-card" key={member.id}>
                  <div>
                    <strong>{member.full_name}</strong>
                    <small>{member.email}</small>
                  </div>
                  <select
                    aria-label={"Rôle de " + member.full_name}
                    value={member.role}
                    onChange={(event) =>
                      memberRoleMutation.mutate({
                        userId: member.id,
                        role: event.target.value as OrganizationRole,
                      })
                    }
                    disabled={memberRoleMutation.isPending}
                  >
                    {ROLES.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Aucun membre"
              detail="Ajoutez le premier responsable de cette organisation."
            />
          )}
          <details open={!members.length && Boolean(organizationId)}>
            <summary>Ajouter un membre</summary>
            <form
              className="compact-form"
              onSubmit={(event) => {
                event.preventDefault();
                memberMutation.mutate();
              }}
            >
              <label>
                Nom complet
                <input
                  value={memberName}
                  onChange={(event) => setMemberName(event.target.value)}
                  required
                  minLength={2}
                />
              </label>
              <label>
                Adresse électronique
                <input
                  type="email"
                  value={memberEmail}
                  onChange={(event) => setMemberEmail(event.target.value)}
                  required
                />
              </label>
              <label>
                Mot de passe initial
                <input
                  type="password"
                  value={memberPassword}
                  onChange={(event) => setMemberPassword(event.target.value)}
                  required
                  minLength={12}
                  autoComplete="new-password"
                />
              </label>
              <label>
                Rôle
                <select
                  value={memberRole}
                  onChange={(event) => setMemberRole(event.target.value as OrganizationRole)}
                >
                  {ROLES.map((role) => (
                    <option key={role.value} value={role.value}>
                      {role.label}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="button button-primary"
                disabled={!organizationId || memberMutation.isPending}
              >
                Créer le membre
              </button>
            </form>
          </details>
        </Panel>

        <Panel
          title="Éditions normatives"
          description="Références acquises ; aucun texte protégé n'est recopié."
        >
          {standards.length ? (
            <div className="card-list">
              {standards.map((standard) => (
                <article className="compact-card" key={standard.id}>
                  <div>
                    <strong>{standard.code} — {standard.title}</strong>
                    <small>{standard.issuing_body} · édition {standard.edition}</small>
                  </div>
                  <div className="inline-actions">
                    <StatusBadge value={standard.status} />
                    {standard.status === "draft" ? (
                      <button
                        className="button button-secondary"
                        onClick={() => approveStandardMutation.mutate(standard.id)}
                        disabled={approveStandardMutation.isPending}
                      >
                        Activer
                      </button>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Aucune référence"
              detail="Enregistrez l'édition vérifiée avant de définir des règles."
            />
          )}
          <details open={!standards.length && Boolean(organizationId)}>
            <summary>Enregistrer une édition</summary>
            <form
              className="compact-form"
              onSubmit={(event) => {
                event.preventDefault();
                standardMutation.mutate();
              }}
            >
              <div className="form-grid">
                <label>
                  Code
                  <input
                    value={standardCode}
                    onChange={(event) => setStandardCode(event.target.value.toUpperCase())}
                    required
                  />
                </label>
                <label>
                  Édition
                  <input
                    value={standardEdition}
                    onChange={(event) => setStandardEdition(event.target.value)}
                    required
                  />
                </label>
              </div>
              <label>
                Titre officiel
                <input
                  value={standardTitle}
                  onChange={(event) => setStandardTitle(event.target.value)}
                  required
                />
              </label>
              <div className="form-grid">
                <label>
                  Organisme émetteur
                  <input
                    value={standardBody}
                    onChange={(event) => setStandardBody(event.target.value)}
                    required
                  />
                </label>
                <label>
                  Date de publication
                  <input
                    type="date"
                    value={standardDate}
                    onChange={(event) => setStandardDate(event.target.value)}
                  />
                </label>
              </div>
              <label>
                Référence de la copie acquise
                <input
                  value={standardCopyReference}
                  onChange={(event) => setStandardCopyReference(event.target.value)}
                  placeholder="coffre-documentaire/reference"
                />
              </label>
              <label>
                Adresse de la source
                <input
                  type="url"
                  value={standardSourceUrl}
                  onChange={(event) => setStandardSourceUrl(event.target.value)}
                  placeholder="https://..."
                />
              </label>
              <button
                className="button button-primary"
                disabled={!organizationId || standardMutation.isPending}
              >
                Enregistrer l'édition
              </button>
            </form>
          </details>
        </Panel>
      </div>

      <Panel
        title="Jeux de règles"
        description="Seules des règles explicites, relues puis figées peuvent être affectées à un projet."
      >
        <div className="form-grid">
          <label>
            Version de règles
            <select
              value={selectedRuleSetId}
              onChange={(event) => setSelectedRuleSetId(event.target.value)}
            >
              <option value="">Sélectionner</option>
              {ruleSets.map((ruleSet) => (
                <option key={ruleSet.id} value={ruleSet.id}>
                  {ruleSet.code} — V{ruleSet.version_number} — {ruleSet.status}
                </option>
              ))}
            </select>
          </label>
          {selectedRuleSet ? (
            <div className="resource-summary">
              <div><span>Statut</span><strong>{selectedRuleSet.status}</strong></div>
              <div><span>Domaine</span><strong>{selectedRuleSet.domain}</strong></div>
              <div><span>Empreinte</span><strong className="mono hash">{selectedRuleSet.content_hash}</strong></div>
            </div>
          ) : null}
        </div>

        {rules.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Règle</th>
                  <th>Métrique</th>
                  <th>Limite</th>
                  <th>Sévérité</th>
                  <th>Statut</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <td><strong>{rule.code}</strong><small>{rule.title}</small></td>
                    <td className="mono">{rule.metric_path}</td>
                    <td>{rule.operator} {rule.limit_value} {rule.unit ?? ""}</td>
                    <td>{rule.severity}</td>
                    <td><StatusBadge value={rule.status} /></td>
                    <td>
                      {rule.status === "draft" ? (
                        <button
                          className="button button-secondary"
                          onClick={() => approveRuleMutation.mutate(rule.id)}
                          disabled={approveRuleMutation.isPending}
                        >
                          Approuver
                        </button>
                      ) : "Figée"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Aucune règle"
            detail="Sélectionnez un jeu ou ajoutez sa première règle contrôlée."
          />
        )}

        {selectedRuleSet?.status === "draft" ? (
          <div className="button-row section-actions">
            <button
              className="button button-primary"
              onClick={() => approveRuleSetMutation.mutate()}
              disabled={approveRuleSetMutation.isPending || !rules.length}
            >
              Approuver et figer le jeu
            </button>
          </div>
        ) : null}

        <div className="content-grid equal nested-grid">
          <details open={!ruleSets.length && Boolean(activeStandards.length)}>
            <summary>Créer un jeu de règles</summary>
            <form
              className="compact-form"
              onSubmit={(event) => {
                event.preventDefault();
                ruleSetMutation.mutate();
              }}
            >
              <div className="form-grid">
                <label>
                  Code
                  <input
                    value={ruleSetCode}
                    onChange={(event) => setRuleSetCode(event.target.value.toUpperCase())}
                    required
                  />
                </label>
                <label>
                  Pays
                  <input
                    value={ruleSetCountry}
                    onChange={(event) =>
                      setRuleSetCountry(event.target.value.toUpperCase().slice(0, 2))
                    }
                    maxLength={2}
                  />
                </label>
              </div>
              <label>
                Titre
                <input
                  value={ruleSetTitle}
                  onChange={(event) => setRuleSetTitle(event.target.value)}
                  required
                />
              </label>
              <label>
                Domaine
                <input
                  value={ruleSetDomain}
                  onChange={(event) => setRuleSetDomain(event.target.value)}
                  required
                />
              </label>
              <label>
                Description
                <textarea
                  value={ruleSetDescription}
                  onChange={(event) => setRuleSetDescription(event.target.value)}
                  rows={3}
                />
              </label>
              <fieldset className="selection-fieldset">
                <legend>Éditions actives</legend>
                {activeStandards.map((standard) => (
                  <label className="selection-option" key={standard.id}>
                    <input
                      type="checkbox"
                      checked={ruleSetStandardIds.includes(standard.id)}
                      onChange={() => toggleStandard(standard.id)}
                    />
                    <span><strong>{standard.code}</strong><small>{standard.title}</small></span>
                  </label>
                ))}
                {!activeStandards.length ? (
                  <p className="field-help">Activez d'abord une édition normative.</p>
                ) : null}
              </fieldset>
              <button
                className="button button-primary"
                disabled={!ruleSetStandardIds.length || ruleSetMutation.isPending}
              >
                Créer la version
              </button>
            </form>
          </details>

          <details open={Boolean(selectedRuleSet && !rules.length)}>
            <summary>Ajouter une règle</summary>
            <form
              className="compact-form"
              onSubmit={(event) => {
                event.preventDefault();
                ruleMutation.mutate();
              }}
            >
              <div className="form-grid">
                <label>
                  Code
                  <input
                    value={ruleCode}
                    onChange={(event) => setRuleCode(event.target.value.toUpperCase())}
                    required
                  />
                </label>
                <label>
                  Sévérité
                  <select
                    value={ruleSeverity}
                    onChange={(event) =>
                      setRuleSeverity(event.target.value as RuleDefinition["severity"])
                    }
                  >
                    <option value="blocking">Bloquante</option>
                    <option value="error">Erreur</option>
                    <option value="warning">Avertissement</option>
                    <option value="information">Information</option>
                  </select>
                </label>
              </div>
              <label>
                Titre
                <input
                  value={ruleTitle}
                  onChange={(event) => setRuleTitle(event.target.value)}
                  required
                />
              </label>
              <label>
                Source normative
                <select
                  value={ruleStandardId}
                  onChange={(event) => setRuleStandardId(event.target.value)}
                >
                  <option value="">Référence interne sans édition</option>
                  {standards
                    .filter((standard) => selectedRuleSet?.standard_ids.includes(standard.id))
                    .map((standard) => (
                      <option key={standard.id} value={standard.id}>{standard.code}</option>
                    ))}
                </select>
              </label>
              <div className="form-grid three">
                <label>
                  Métrique
                  <input
                    list="calculation-metrics"
                    value={ruleMetric}
                    onChange={(event) => setRuleMetric(event.target.value)}
                    required
                  />
                  <datalist id="calculation-metrics">
                    {METRICS.map((metric) => <option key={metric} value={metric} />)}
                  </datalist>
                </label>
                <label>
                  Opérateur
                  <select
                    value={ruleOperator}
                    onChange={(event) =>
                      setRuleOperator(event.target.value as RuleDefinition["operator"])
                    }
                  >
                    <option value="le">≤</option>
                    <option value="lt">&lt;</option>
                    <option value="ge">≥</option>
                    <option value="gt">&gt;</option>
                    <option value="eq">=</option>
                    <option value="between">Entre deux bornes</option>
                  </select>
                </label>
                <label>
                  Limite basse ou unique
                  <input
                    type="number"
                    step="any"
                    value={ruleLimit}
                    onChange={(event) => setRuleLimit(event.target.value)}
                    required
                  />
                </label>
              </div>
              {ruleOperator === "between" ? (
                <label>
                  Limite haute
                  <input
                    type="number"
                    step="any"
                    value={ruleUpperLimit}
                    onChange={(event) => setRuleUpperLimit(event.target.value)}
                    required
                  />
                </label>
              ) : null}
              <label>
                Unité
                <input value={ruleUnit} onChange={(event) => setRuleUnit(event.target.value)} />
              </label>
              <label>
                Message de non-conformité
                <textarea
                  value={ruleMessage}
                  onChange={(event) => setRuleMessage(event.target.value)}
                  required
                  rows={3}
                />
              </label>
              <label>
                Clause source
                <input
                  value={ruleClause}
                  onChange={(event) => setRuleClause(event.target.value)}
                />
              </label>
              <button
                className="button button-primary"
                disabled={selectedRuleSet?.status !== "draft" || ruleMutation.isPending}
              >
                Ajouter la règle
              </button>
            </form>
          </details>
        </div>
      </Panel>

      <Panel title="Journal d'audit" description="Trente événements les plus récents.">
        {auditEvents.length ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Action</th><th>Objet</th><th>Identifiant</th></tr></thead>
              <tbody>
                {auditEvents.map((event) => (
                  <tr key={event.id}>
                    <td>{formatDate(event.created_at)}</td>
                    <td className="mono">{event.action}</td>
                    <td>{event.object_type}</td>
                    <td className="mono hash">{event.object_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Journal vide" detail="Les actions métier apparaîtront ici." />
        )}
      </Panel>
    </div>
  );
}
