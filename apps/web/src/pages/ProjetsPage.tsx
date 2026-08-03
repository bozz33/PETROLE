import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest, jsonBody } from "../api";
import { EmptyState, ErrorNotice, Panel, StatusBadge, SuccessNotice } from "../components/Shell";
import { EXAMPLE_MODEL } from "../samples";
import type { ModelVersion, Organization, Page, Project, Site } from "../types";
import { formatDate } from "../types";

export function ProjetsPage() {
  const queryClient = useQueryClient();
  const [organizationId, setOrganizationId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [organizationSlug, setOrganizationSlug] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectCode, setProjectCode] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [projectSiteId, setProjectSiteId] = useState("");
  const [siteName, setSiteName] = useState("");
  const [siteCode, setSiteCode] = useState("");
  const [modelName, setModelName] = useState("Baseline hydraulique");
  const [modelPayload, setModelPayload] = useState(
    JSON.stringify(EXAMPLE_MODEL, null, 2),
  );

  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<Page<Organization>>("/organizations?limit=200&offset=0"),
  });
  const sitesQuery = useQuery({
    queryKey: ["sites", organizationId],
    queryFn: () =>
      apiRequest<Page<Site>>(
        "/sites?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });  const projectsQuery = useQuery({
    queryKey: ["projects", organizationId],
    queryFn: () =>
      apiRequest<Page<Project>>(
        "/projects?limit=200&offset=0&organization_id=" + organizationId,
      ),
    enabled: Boolean(organizationId),
  });
  const modelsQuery = useQuery({
    queryKey: ["models", projectId],
    queryFn: () =>
      apiRequest<Page<ModelVersion>>(
        "/projects/" + projectId + "/models?limit=200&offset=0",
      ),
    enabled: Boolean(projectId),
  });

  const organizations = organizationsQuery.data?.items ?? [];
  const sites = sitesQuery.data?.items ?? [];
  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];

  useEffect(() => {
    if (!organizationId && organizations.length) {
      setOrganizationId(organizations[0].id);
    }
  }, [organizationId, organizations]);

  useEffect(() => {
    if (!projectId || !projects.some((project) => project.id === projectId)) {
      setProjectId(projects[0]?.id ?? "");
    }
  }, [projectId, projects]);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === projectId),
    [projectId, projects],
  );

  const organizationMutation = useMutation({
    mutationFn: () =>
      apiRequest<Organization>("/organizations", {
        method: "POST",
        body: jsonBody({
          name: organizationName,
          slug: organizationSlug,
          default_locale: "fr",
          default_unit_system: "SI",
        }),
      }),
    onSuccess: async (organization) => {
      setOrganizationName("");
      setOrganizationSlug("");
      setOrganizationId(organization.id);
      await queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });

  const siteMutation = useMutation({
    mutationFn: () =>
      apiRequest<Site>("/sites", {
        method: "POST",
        body: jsonBody({
          organization_id: organizationId,
          name: siteName,
          code: siteCode,
        }),
      }),
    onSuccess: async (site) => {
      setSiteName("");
      setSiteCode("");
      setProjectSiteId(site.id);
      await queryClient.invalidateQueries({ queryKey: ["sites", organizationId] });
    },
  });
  const projectMutation = useMutation({
    mutationFn: () =>
      apiRequest<Project>("/projects", {
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
    mutationFn: () => {
      const payload = JSON.parse(modelPayload) as Record<string, unknown>;
      return apiRequest<ModelVersion>("/projects/" + projectId + "/models", {
        method: "POST",
        body: jsonBody({ name: modelName, payload }),
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["models", projectId] });
    },
  });

  const approveMutation = useMutation({
    mutationFn: (modelId: string) =>
      apiRequest<ModelVersion>("/models/" + modelId + "/approve", {
        method: "POST",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["models", projectId] });
    },
  });

  const error =
    organizationsQuery.error ??
    sitesQuery.error ??
    projectsQuery.error ??
    modelsQuery.error ??
    organizationMutation.error ??
    siteMutation.error ??
    projectMutation.error ??
    modelMutation.error ??
    approveMutation.error;

  return (
    <div className="stack">
      {error ? <ErrorNotice error={error} /> : null}
      {(organizationMutation.isSuccess ||
        siteMutation.isSuccess ||
        projectMutation.isSuccess ||
        modelMutation.isSuccess ||
        approveMutation.isSuccess) && (
        <SuccessNotice>La modification a été enregistrée et auditée.</SuccessNotice>
      )}

      <div className="content-grid equal">
        <Panel
          title="Contexte de travail"
          description="Sélectionnez l'organisation et le projet actifs."
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
              Projet
              <select
                value={projectId}
                onChange={(event) => setProjectId(event.target.value)}
                disabled={!organizationId}
              >
                <option value="">Sélectionner</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.code} — {project.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {selectedProject ? (
            <dl className="detail-list">
              <div>
                <dt>Statut</dt>
                <dd>
                  <StatusBadge value={selectedProject.status} />
                </dd>
              </div>
              <div>
                <dt>Pays</dt>
                <dd>{selectedProject.country_code?.toUpperCase() ?? "Non défini"}</dd>
              </div>
              <div>
                <dt>Dernière modification</dt>
                <dd>{formatDate(selectedProject.updated_at)}</dd>
              </div>
            </dl>
          ) : (
            <EmptyState
              title="Aucun contexte sélectionné"
              detail="Créez d'abord une organisation puis un projet."
            />
          )}
        </Panel>

        <Panel title="Créer le référentiel" description="Ajout rapide sans quitter la page.">
          <details open={!organizations.length}>
            <summary>Nouvelle organisation</summary>
            <form
              className="compact-form"
              onSubmit={(event) => {
                event.preventDefault();
                organizationMutation.mutate();
              }}
            >
              <label>
                Nom
                <input
                  value={organizationName}
                  onChange={(event) => setOrganizationName(event.target.value)}
                  required
                  minLength={2}
                />
              </label>
              <label>
                Identifiant URL
                <input
                  value={organizationSlug}
                  onChange={(event) => setOrganizationSlug(event.target.value)}
                  required
                  pattern="[a-z0-9-]+"
                  placeholder="operateur-nord"
                />
              </label>
              <button
                className="button button-primary"
                disabled={organizationMutation.isPending}
              >
                Créer l'organisation
              </button>
            </form>
          </details>
          <details open={Boolean(organizationId && !sites.length)}>
            <summary>Nouveau site industriel</summary>
            <form
              className="compact-form"
              onSubmit={(event) => {
                event.preventDefault();
                siteMutation.mutate();
              }}
            >
              <label>
                Nom du site
                <input value={siteName} onChange={(event) => setSiteName(event.target.value)} required />
              </label>
              <label>
                Code du site
                <input value={siteCode} onChange={(event) => setSiteCode(event.target.value.toUpperCase())} required />
              </label>
              <button className="button button-primary" disabled={!organizationId || siteMutation.isPending}>
                Créer le site
              </button>
            </form>
          </details>          <details open={Boolean(organizations.length && !projects.length)}>
            <summary>Nouveau projet</summary>
            <form
              className="compact-form"
              onSubmit={(event) => {
                event.preventDefault();
                projectMutation.mutate();
              }}
            >
              <label>
                Site industriel
                <select value={projectSiteId} onChange={(event) => setProjectSiteId(event.target.value)}>
                  <option value="">Aucun site</option>
                  {sites.map((site) => (
                    <option key={site.id} value={site.id}>{site.code} — {site.name}</option>
                  ))}
                </select>
              </label>              <label>
                Nom
                <input
                  value={projectName}
                  onChange={(event) => setProjectName(event.target.value)}
                  required
                />
              </label>
              <div className="form-grid">
                <label>
                  Code
                  <input
                    value={projectCode}
                    onChange={(event) => setProjectCode(event.target.value.toUpperCase())}
                    required
                  />
                </label>
                <label>
                  Pays
                  <input
                    value={countryCode}
                    onChange={(event) => setCountryCode(event.target.value.slice(0, 2))}
                    maxLength={2}
                    placeholder="DZ"
                  />
                </label>
              </div>
              <button
                className="button button-primary"
                disabled={!organizationId || projectMutation.isPending}
              >
                Créer le projet
              </button>
            </form>
          </details>
        </Panel>
      </div>

      <Panel
        title="Versions du modèle"
        description="Une version approuvée est figée ; toute variante conserve sa filiation."
      >
        {models.length ? (
          <div className="version-grid">
            {models.map((model) => (
              <article className="version-card" key={model.id}>
                <div>
                  <span>V{model.version_number}</span>
                  <StatusBadge value={model.status} />
                </div>
                <h3>{model.name}</h3>
                <p className="mono hash">{model.content_hash}</p>
                <small>Créée le {formatDate(model.created_at)}</small>
                {model.status === "draft" ? (
                  <button
                    className="button button-secondary"
                    onClick={() => approveMutation.mutate(model.id)}
                    disabled={approveMutation.isPending}
                  >
                    Approuver et figer
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            title="Aucune version"
            detail="Ajoutez une première version JSON du réseau et du fluide."
          />
        )}

        <details className="editor-details" open={!models.length && Boolean(projectId)}>
          <summary>Ajouter une version de modèle</summary>
          <form
            className="editor-form"
            onSubmit={(event) => {
              event.preventDefault();
              modelMutation.mutate();
            }}
          >
            <label>
              Nom de la version
              <input
                value={modelName}
                onChange={(event) => setModelName(event.target.value)}
                required
              />
            </label>
            <label>
              Modèle canonique
              <textarea
                className="code-editor"
                value={modelPayload}
                onChange={(event) => setModelPayload(event.target.value)}
                spellCheck={false}
                rows={22}
              />
            </label>
            <div className="button-row">
              <button
                className="button button-primary"
                disabled={!projectId || modelMutation.isPending}
              >
                Enregistrer la version
              </button>
              <button
                className="button button-ghost"
                type="button"
                onClick={() => setModelPayload(JSON.stringify(EXAMPLE_MODEL, null, 2))}
              >
                Restaurer l'exemple
              </button>
            </div>
          </form>
        </details>
      </Panel>
    </div>
  );
}
