/**
 * Résolution de l'espace de données courant selon le mode de déploiement.
 *
 * En mode mono-exploitant, l'organisation est imposée par le serveur : elle
 * cesse d'être une donnée que l'ingénieur choisit. Les pages métier consomment
 * ce module au lieu de charger et d'exposer une liste d'organisations.
 */

import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "./api";
import type { Health, Organization, Page } from "./types";

export interface DeploymentScope {
  /** Vrai lorsque l'instance ne sert qu'un seul exploitant. */
  singleOrganization: boolean;
  /** Intitulé à afficher : « Exploitant » ou « Organisations ». */
  label: string;
  /** Organisations accessibles ; une seule en mode mono-exploitant. */
  organizations: Organization[];
  /** Organisation courante, résolue sans intervention de l'utilisateur. */
  organization: Organization | null;
  /** Identifiant de l'organisation courante, chaîne vide si indisponible. */
  organizationId: string;
  loading: boolean;
  error: unknown;
}

export function useDeploymentScope(): DeploymentScope {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: () => apiRequest<Health>("/health"),
    staleTime: 60_000,
  });
  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<Page<Organization>>("/organizations?limit=200&offset=0"),
    staleTime: 60_000,
  });

  const organizations = organizationsQuery.data?.items ?? [];
  const deployment = healthQuery.data?.deployment;
  const singleOrganization = deployment?.mode === "single_org";

  return {
    singleOrganization,
    label: deployment?.organization_label ?? (singleOrganization ? "Exploitant" : "Organisations"),
    organizations,
    organization: organizations[0] ?? null,
    organizationId: organizations[0]?.id ?? "",
    loading: healthQuery.isLoading || organizationsQuery.isLoading,
    error: healthQuery.error ?? organizationsQuery.error,
  };
}
