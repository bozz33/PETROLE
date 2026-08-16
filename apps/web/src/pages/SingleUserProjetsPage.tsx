import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { OrganizationField } from "../components/OrganizationField";
import { apiRequest, jsonBody } from "../api";
import { EmptyState, ErrorNotice, Panel, StatusBadge, SuccessNotice } from "../components/Shell";
import { EXAMPLE_MODEL } from "../samples";
import type { ModelVersion, Page, Project, RuleSet, Site } from "../types";
import { formatDate } from "../types";

export function SingleUserProjetsPage() {
  const queryClient = useQueryClient();
  const [organizationId, setOrganizationId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectCode, setProjectCode] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [projectSiteId, setProjectSiteId] = useState("");
  const [siteName, setSiteName] = useState("");
  const [siteCode, setSiteCode] = useState("");

  const [configuredName, setConfiguredName] = useState("");
  const [configuredDescription, setConfiguredDescription] = useState("");
  const [configuredCountryCode, setConfiguredCountryCode] = useState("");
  const [configuredSiteId, setConfiguredSiteId] = useState("");
  const [configuredProjectType, setConfiguredProjectType] = useState<Project["project_type"]>("liquid_pipeline");
  const [selectedRuleSetIds, setSelectedRuleSetIds] = useState<string[]>([]);

  const [modelName, setModelName] = useState("Baseline hydraulique");
  const [modelPayload, setModelPayload] = useState(JSON.stringify(EXAMPLE_MODEL, null, 2));

  const sitesQuery = useQuery({
    queryKey: ["sites", organizationId],
    queryFn: () => apiRequest<Page<Site>>("/sites?limit=200&offset=0&organization_id=" + organizationId),
    enabled: Boolean(organizationId),
  });
  const projectsQuery = useQuery({
    queryKey: ["projects", organizationId],
    queryFn: () => apiRequest<Page<Project>>("/projects?include_archived=true&limit=200&offset=0&organization_id=" + organizationId),
    enabled: Boolean(organizationId),
  });
  const modelsQuery = useQuery({
    queryKey: ["models", projectId],
    queryFn: () => apiRequest<Page<ModelVersion>>("/projects/" + projectId + "/models?limit=200&offset=0"),
    enabled: Boolean(projectId),
  });
  const ruleSetsQuery = useQuery({
    queryKey: ["rule-sets", organizationId, "available"],
    queryFn: () => apiRequest<Page<RuleSet>>("/rule-sets?status=approved&limit=200&offset=0&organization_id=" + organizationId),
    enabled: Boolean(organizationId),
  });

  const sites = sitesQuery.data?.items ?? [];
  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];
  const availableRuleSets = ruleSetsQuery.data?.items ?? [];

  useEffect(() => {
    if (!projectId || !projects.some((project) => project.id === projectId)) {
      setProjectId(projects[0]?.id ?? "");
    }
  }, [projectId, projects]);

  const selectedProject = useMemo(() => projects.find((project) => project.id === projectId), [projectId, projects]);

  useEffect(() => {
    if (!selectedProject) {
      setConfiguredName("");
      setConfiguredDescription("");
      setConfiguredCountryCode("");
      setConfiguredSiteId("");
      setConfiguredProjectType("liquid_pipeline");
      setSelectedRuleSetIds([]);
      return;
    }
    setConfiguredName(selectedProject.name);
    setConfiguredDescription(selectedProject.description ?? "");
    setConfiguredCountryCode(selectedProject.country_code ?? "");
    setConfiguredSiteId(selectedProject.site_id ?? "");
    setConfiguredProjectType(selectedProject.project_type);
    setSelectedRuleSetIds(selectedProject.rule_set_ids);
  }, [selectedProject]);

  const siteMutation = useMutation({
    mutationFn: () => apiRequest<Site>("/sites", {
      method: "POST",
      body: jsonBody({ organization_id: organizationId, name: siteName, code: siteCode }),
    }),
    onSuccess: async (site) => {
      setSiteName("");
      setSiteCode("");
      setProjectSiteId(site.id);
      await queryClient.invalidateQueries({ queryKey: ["sites", organizationId] });
    },
  });

  const projectMutation = useMutation({
    mutationFn: () => apiRequest<Project>("/projects", {
      method: "POST",
      body: jsonBody({
        organization_id: organizationId,
        site_id: projectSiteId || null,
        name: projectName,
        code: projectCode,
        country_code: countryCode || null,
      }),
    }),
    onSuccess: async (project) => {
      setProjectName("");
      setProjectCode("");
      setCountryCode("");
      setProjectId(project.id);
      await queryClient.invalidateQueries({ queryKey: ["projects", organizationId] });
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const modelMutation = useMutation({
    mutationFn: () => apiRequest<ModelVersion>("/projects/" + projectId + "/models", {
      method: "POST",
      body: jsonBody({ name: modelName, payload: JSON.parse(modelPayload) as Record<string, unknown> }),
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["models", projectId] });
    },
  });

  const projectConfigurationMutation = useMutation({
    mutationFn: () => apiRequest<Project>("/projects/" + projectId, {
      method: "PATCH",
      body: jsonBody({
        name: configuredName,
        description: configuredDescription || null,
        project_type: configuredProjectType,
        country_code: configuredCountryCode || null,
        site_id: configuredSiteId || null,
        rule_set_ids: selectedRuleSetIds,
      }),
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects", organizationId] });
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const projectStatusMutation = useMutation({
    mutationFn: (action: "activate" | "archive" | "restore") => apiRequest<Project>("/projects/" + projectId + "/" + action, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects", organizationId] });
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  function toggleRuleSet(identifier: string): void {
    setSelectedRuleSetIds((current) => current.includes(identifier) ? current.filter((value) => value !== identifier) : [...current, identifier]);
  }

  const error =
    sitesQuery.error ?? projectsQuery.error ?? modelsQuery.error ?? ruleSetsQuery.error ??
    siteMutation.error ?? projectMutation.error ?? modelMutation.error ??
    projectConfigurationMutation.error ?? projectStatusMutation.error;
  const success = siteMutation.isSuccess || projectMutation.isSuccess || modelMutation.isSuccess || projectConfigurationMutation.isSuccess || projectStatusMutation.isSuccess;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {success ? <SuccessNotice>La modification a été enregistrée et auditée.</SuccessNotice> : null}

      <Panel
        title="Contexte de travail"
        description="L'ingénieur unique crée et gère directement ses sites, projets et versions de modèle."
      >
        <div className="form-grid">
          <OrganizationField value={organizationId} onChange={setOrganizationId} />
          <label>
            Projet
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)} disabled={!organizationId}>
              <option value="">Sélectionner</option>
              {projects.map((project) => <option key={project.id} value={project.id}>{project.code} — {project.name}</option>)}
            </select>
          </label>
        </div>
        {selectedProject ? (
          <dl className="detail-list">
            <div><dt>Statut</dt><dd><StatusBadge value={selectedProject.status} /></dd></div>
            <div><dt>Pays</dt><dd>{selectedProject.country_code?.toUpperCase() ?? "Non défini"}</dd></div>
            <div><dt>Dernière modification</dt><dd>{formatDate(selectedProject.updated_at)}</dd></div>
          </dl>
        ) : <EmptyState title="Aucun projet" detail="Créez un site puis votre premier projet." />}
      </Panel>

      <div className="content-grid equal">
        <Panel title="Nouveau site" description="Référentiel physique de l'installation.">
          <form className="compact-form" onSubmit={(event) => { event.preventDefault(); siteMutation.mutate(); }}>
            <label>Nom du site<input value={siteName} onChange={(event) => setSiteName(event.target.value)} required /></label>
            <label>Code du site<input value={siteCode} onChange={(event) => setSiteCode(event.target.value.toUpperCase())} required /></label>
            <button className="button button-primary" disabled={!organizationId || siteMutation.isPending}>Créer le site</button>
          </form>
        </Panel>

        <Panel title="Nouveau projet" description="Projet d'étude géré directement par l'ingénieur.">
          <form className="compact-form" onSubmit={(event) => { event.preventDefault(); projectMutation.mutate(); }}>
            <label>Site<select value={projectSiteId} onChange={(event) => setProjectSiteId(event.target.value)}><option value="">Aucun site</option>{sites.map((site) => <option key={site.id} value={site.id}>{site.code} — {site.name}</option>)}</select></label>
            <label>Nom<input value={projectName} onChange={(event) => setProjectName(event.target.value)} required /></label>
            <div className="form-grid">
              <label>Code<input value={projectCode} onChange={(event) => setProjectCode(event.target.value.toUpperCase())} required /></label>
              <label>Pays<input value={countryCode} onChange={(event) => setCountryCode(event.target.value.slice(0, 2).toUpperCase())} maxLength={2} /></label>
            </div>
            <button className="button button-primary" disabled={!organizationId || projectMutation.isPending}>Créer le projet</button>
          </form>
        </Panel>
      </div>

      <Panel title="Fiche projet" description="Configuration métier, référentiels de règles et cycle de vie du projet.">
        {selectedProject ? (
          <form className="editor-form" onSubmit={(event) => { event.preventDefault(); projectConfigurationMutation.mutate(); }}>
            <div className="form-grid three">
              <label>Nom<input value={configuredName} onChange={(event) => setConfiguredName(event.target.value)} required /></label>
              <label>Type<select value={configuredProjectType} onChange={(event) => setConfiguredProjectType(event.target.value as Project["project_type"])}><option value="liquid_pipeline">Pipeline liquide</option><option value="terminal">Terminal</option><option value="gas_pipeline">Pipeline gaz</option><option value="combined">Combiné</option></select></label>
              <label>Pays<input value={configuredCountryCode} onChange={(event) => setConfiguredCountryCode(event.target.value.slice(0, 2).toUpperCase())} maxLength={2} /></label>
            </div>
            <label>Description<textarea rows={3} value={configuredDescription} onChange={(event) => setConfiguredDescription(event.target.value)} /></label>
            <label>Site<select value={configuredSiteId} onChange={(event) => setConfiguredSiteId(event.target.value)}><option value="">Aucun site</option>{sites.map((site) => <option key={site.id} value={site.id}>{site.code} — {site.name}</option>)}</select></label>

            <fieldset className="selection-fieldset">
              <legend>Jeux de règles à appliquer</legend>
              {availableRuleSets.length ? availableRuleSets.map((ruleSet) => (
                <label className="selection-option" key={ruleSet.id}>
                  <input type="checkbox" checked={selectedRuleSetIds.includes(ruleSet.id)} onChange={() => toggleRuleSet(ruleSet.id)} />
                  <span><strong>{ruleSet.code}</strong><small>{ruleSet.title}</small></span>
                </label>
              )) : <p className="field-help">Aucun jeu de règles disponible. Créez-en un dans Administration.</p>}
            </fieldset>

            <div className="button-row">
              <button className="button button-primary" disabled={projectConfigurationMutation.isPending}>Enregistrer la fiche</button>
              {selectedProject.status === "draft" ? <button type="button" className="button button-secondary" onClick={() => projectStatusMutation.mutate("activate")}>Activer le projet</button> : null}
              {selectedProject.status !== "archived" ? <button type="button" className="button button-ghost" onClick={() => projectStatusMutation.mutate("archive")}>Archiver</button> : <button type="button" className="button button-secondary" onClick={() => projectStatusMutation.mutate("restore")}>Restaurer</button>}
            </div>
          </form>
        ) : <EmptyState title="Projet requis" detail="Sélectionnez un projet pour afficher sa fiche." />}
      </Panel>

      <Panel
        title="Versions de modèle"
        description="Les versions restent éditables jusqu'à leur archivage. Il n'existe plus d'étape d'approbation séparée."
      >
        {projectId ? (
          <>
            <form className="editor-form" onSubmit={(event) => { event.preventDefault(); modelMutation.mutate(); }}>
              <label>Nom de la version<input value={modelName} onChange={(event) => setModelName(event.target.value)} required /></label>
              <label>Charge utile initiale<textarea className="code-editor" rows={12} spellCheck={false} value={modelPayload} onChange={(event) => setModelPayload(event.target.value)} /></label>
              <button className="button button-primary" disabled={modelMutation.isPending}>Créer la version</button>
            </form>

            {models.length ? (
              <div className="table-wrap">
                <table><thead><tr><th>Version</th><th>Nom</th><th>État</th><th>Empreinte</th></tr></thead><tbody>
                  {models.map((model) => (
                    <tr key={model.id}>
                      <td>V{model.version_number}</td>
                      <td>{model.name}</td>
                      <td><StatusBadge value={model.status === "draft" ? "editable" : model.status} /></td>
                      <td className="mono hash">{model.content_hash}</td>
                    </tr>
                  ))}
                </tbody></table>
              </div>
            ) : <EmptyState title="Aucune version" detail="Créez la baseline de votre projet." />}
          </>
        ) : <EmptyState title="Projet requis" detail="Sélectionnez un projet avant de créer une version." />}
      </Panel>
    </div>
  );
}
