import { useEffect } from "react";

import { useDeploymentScope } from "../deployment";

interface OrganizationFieldProps {
  value: string;
  onChange: (organizationId: string) => void;
}

/**
 * Champ d'espace de données.
 *
 * En mode mono-exploitant, l'organisation est imposée par le serveur : le champ
 * devient une mention en lecture seule et se sélectionne tout seul. En mode
 * multi-organisations, il redevient un vrai sélecteur.
 */
export function OrganizationField({ value, onChange }: OrganizationFieldProps) {
  const { singleOrganization, label, organizations, organizationId } = useDeploymentScope();

  useEffect(() => {
    if (singleOrganization) {
      if (organizationId && value !== organizationId) {
        onChange(organizationId);
      }
      return;
    }
    if (!organizations.some((organization) => organization.id === value)) {
      onChange(organizations[0]?.id ?? "");
    }
  }, [onChange, organizationId, organizations, singleOrganization, value]);

  if (singleOrganization) {
    return (
      <label>
        {label}
        <input
          value={organizations[0]?.name ?? "Espace non initialisé"}
          readOnly
          tabIndex={-1}
          aria-readonly="true"
        />
      </label>
    );
  }

  return (
    <label>
      Organisation
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Sélectionner</option>
        {organizations.map((organization) => (
          <option key={organization.id} value={organization.id}>
            {organization.name}
          </option>
        ))}
      </select>
    </label>
  );
}
