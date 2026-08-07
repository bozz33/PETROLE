/**
 * Compléments d'un tronçon : géométrie mécanique, profil altimétrique et
 * accessoires. Ces informations existaient dans le contrat backend mais
 * n'étaient accessibles que par un objet libre saisi à la main.
 */

import type { EdgeFitting, EdgeGeometry, ProfilePoint } from "../../types";

const FITTING_KINDS: Array<{ value: string; label: string }> = [
  { value: "elbow", label: "Coude" },
  { value: "tee", label: "Té" },
  { value: "reducer", label: "Réduction" },
  { value: "expander", label: "Élargissement" },
  { value: "filter", label: "Filtre" },
  { value: "valve", label: "Vanne" },
  { value: "check_valve", label: "Clapet" },
  { value: "entrance", label: "Entrée" },
  { value: "exit", label: "Sortie" },
  { value: "custom", label: "Autre accessoire" },
];

export function defaultEdgeGeometry(): EdgeGeometry {
  return {
    outer_diameter_m: null,
    wall_thickness_m: null,
    minimum_pressure_pa: null,
  };
}

/**
 * Profil initial : deux points reliant les altitudes des nœuds encadrants.
 * L'API exige un profil croissant couvrant exactement la longueur du tronçon.
 */
export function defaultProfile(
  lengthM: number,
  fromElevationM: number,
  toElevationM: number,
): ProfilePoint[] {
  return [
    { chainage_m: 0, elevation_m: fromElevationM, latitude: null, longitude: null },
    { chainage_m: lengthM, elevation_m: toElevationM, latitude: null, longitude: null },
  ];
}

export function validateEdgeDetails(
  lengthM: number,
  geometry: EdgeGeometry,
  innerDiameterM: number,
  profile: ProfilePoint[],
  fittings: EdgeFitting[],
): string[] {
  const problems: string[] = [];

  if (
    geometry.outer_diameter_m !== null &&
    geometry.outer_diameter_m <= innerDiameterM
  ) {
    problems.push("Le diamètre extérieur doit dépasser le diamètre intérieur.");
  }
  if (
    geometry.outer_diameter_m !== null &&
    geometry.wall_thickness_m !== null &&
    Math.abs(geometry.outer_diameter_m - 2 * geometry.wall_thickness_m - innerDiameterM) > 1e-6
  ) {
    problems.push(
      "Diamètre extérieur, épaisseur et diamètre intérieur sont incohérents : " +
        "extérieur moins deux épaisseurs doit donner l'intérieur.",
    );
  }

  if (profile.length < 2) {
    problems.push("Le profil doit comporter au moins deux points.");
  } else {
    const increasing = profile.every(
      (point, index) => index === 0 || point.chainage_m > profile[index - 1].chainage_m,
    );
    if (!increasing) {
      problems.push("Les chaînages du profil doivent être strictement croissants.");
    }
    if (Math.abs(profile[0].chainage_m) > 1e-6) {
      problems.push("Le profil doit commencer au chaînage zéro.");
    }
    if (Math.abs(profile[profile.length - 1].chainage_m - lengthM) > 1e-6) {
      problems.push("Le dernier point du profil doit correspondre à la longueur du tronçon.");
    }
  }

  for (const fitting of fittings) {
    if (!fitting.id.trim()) {
      problems.push("Chaque accessoire doit porter un identifiant.");
      break;
    }
  }
  if (fittings.some((fitting) => fitting.chainage_m !== null && fitting.chainage_m > lengthM)) {
    problems.push("Un accessoire est positionné au-delà de la fin du tronçon.");
  }

  return problems;
}

interface EdgeDetailsFormProps {
  lengthM: number;
  geometry: EdgeGeometry;
  onGeometryChange: (value: EdgeGeometry) => void;
  profile: ProfilePoint[];
  onProfileChange: (value: ProfilePoint[]) => void;
  fittings: EdgeFitting[];
  onFittingsChange: (value: EdgeFitting[]) => void;
}

export function EdgeDetailsForm({
  lengthM,
  geometry,
  onGeometryChange,
  profile,
  onProfileChange,
  fittings,
  onFittingsChange,
}: EdgeDetailsFormProps) {
  return (
    <div className="stack">
      <fieldset className="field-group">
        <legend>Géométrie mécanique</legend>
        <div className="form-grid three">
          <label>
            Diamètre extérieur (mm)
            <input
              type="number"
              step="0.1"
              min="0"
              value={text(scale(geometry.outer_diameter_m, 1000))}
              onChange={(event) =>
                onGeometryChange({
                  ...geometry,
                  outer_diameter_m: unscale(number(event.target.value), 1000),
                })
              }
            />
          </label>
          <label>
            Épaisseur de paroi (mm)
            <input
              type="number"
              step="0.1"
              min="0"
              value={text(scale(geometry.wall_thickness_m, 1000))}
              onChange={(event) =>
                onGeometryChange({
                  ...geometry,
                  wall_thickness_m: unscale(number(event.target.value), 1000),
                })
              }
            />
          </label>
          <label>
            Pression minimale admissible (bar abs.)
            <input
              type="number"
              step="0.01"
              min="0"
              value={text(scale(geometry.minimum_pressure_pa, 1e-5))}
              onChange={(event) =>
                onGeometryChange({
                  ...geometry,
                  minimum_pressure_pa: unscale(number(event.target.value), 1e-5),
                })
              }
            />
            <small>Contrôlée après calcul, en complément de la pression de vapeur.</small>
          </label>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Profil altimétrique</legend>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Chaînage (m)</th>
                <th>Altitude (m)</th>
                <th>Latitude</th>
                <th>Longitude</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {profile.map((point, index) => (
                <tr key={index}>
                  <td>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={String(point.chainage_m)}
                      onChange={(event) =>
                        onProfileChange(
                          replaceAt(profile, index, {
                            chainage_m: number(event.target.value) ?? 0,
                          }),
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="any"
                      value={String(point.elevation_m)}
                      onChange={(event) =>
                        onProfileChange(
                          replaceAt(profile, index, {
                            elevation_m: number(event.target.value) ?? 0,
                          }),
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="any"
                      min="-90"
                      max="90"
                      value={text(point.latitude)}
                      onChange={(event) =>
                        onProfileChange(
                          replaceAt(profile, index, { latitude: number(event.target.value) }),
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="any"
                      min="-180"
                      max="180"
                      value={text(point.longitude)}
                      onChange={(event) =>
                        onProfileChange(
                          replaceAt(profile, index, { longitude: number(event.target.value) }),
                        )
                      }
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="button button-ghost"
                      disabled={profile.length <= 2}
                      onClick={() =>
                        onProfileChange(profile.filter((_, current) => current !== index))
                      }
                    >
                      Retirer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="button-row">
          <button
            type="button"
            className="button button-ghost"
            onClick={() => onProfileChange(insertIntermediatePoint(profile))}
          >
            Ajouter un point intermédiaire
          </button>
        </div>
        <p className="field-help">
          Le profil doit partir du chaînage zéro et se terminer exactement à {formatLength(lengthM)}.
          Un profil détaillé permet de détecter les points hauts et les zones gravitaires.
        </p>
      </fieldset>

      <fieldset className="field-group">
        <legend>Accessoires du tronçon</legend>
        {fittings.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Repère</th>
                  <th>Type</th>
                  <th>K</th>
                  <th>Quantité</th>
                  <th>Chaînage (m)</th>
                  <th>Ouverture</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {fittings.map((fitting, index) => (
                  <tr key={index}>
                    <td>
                      <input
                        value={fitting.id}
                        onChange={(event) =>
                          onFittingsChange(
                            replaceAt(fittings, index, { id: event.target.value.toUpperCase() }),
                          )
                        }
                        required
                      />
                    </td>
                    <td>
                      <select
                        value={fitting.kind}
                        onChange={(event) =>
                          onFittingsChange(replaceAt(fittings, index, { kind: event.target.value }))
                        }
                      >
                        {FITTING_KINDS.map((kind) => (
                          <option key={kind.value} value={kind.value}>
                            {kind.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={String(fitting.k_coefficient)}
                        onChange={(event) =>
                          onFittingsChange(
                            replaceAt(fittings, index, {
                              k_coefficient: number(event.target.value) ?? 0,
                            }),
                          )
                        }
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        step="1"
                        min="1"
                        value={String(fitting.quantity)}
                        onChange={(event) =>
                          onFittingsChange(
                            replaceAt(fittings, index, { quantity: number(event.target.value) ?? 1 }),
                          )
                        }
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        step="any"
                        min="0"
                        value={text(fitting.chainage_m)}
                        onChange={(event) =>
                          onFittingsChange(
                            replaceAt(fittings, index, { chainage_m: number(event.target.value) }),
                          )
                        }
                        placeholder="Sur tout le tronçon"
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max="1"
                        value={String(fitting.opening_ratio)}
                        onChange={(event) =>
                          onFittingsChange(
                            replaceAt(fittings, index, {
                              opening_ratio: number(event.target.value) ?? 1,
                            }),
                          )
                        }
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="button button-ghost"
                        onClick={() =>
                          onFittingsChange(fittings.filter((_, current) => current !== index))
                        }
                      >
                        Retirer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="field-help">Aucun accessoire déclaré sur ce tronçon.</p>
        )}
        <div className="button-row">
          <button
            type="button"
            className="button button-ghost"
            onClick={() =>
              onFittingsChange([
                ...fittings,
                {
                  id: "ACC-" + String(fittings.length + 1).padStart(2, "0"),
                  kind: "elbow",
                  k_coefficient: 0.3,
                  quantity: 1,
                  chainage_m: null,
                  opening_ratio: 1,
                },
              ])
            }
          >
            Ajouter un accessoire
          </button>
        </div>
        <p className="field-help">
          Un taux d'ouverture inférieur à 1 modélise une vanne partiellement fermée ou un
          filtre colmaté.
        </p>
      </fieldset>
    </div>
  );
}

/** Insère un point au milieu du plus grand intervalle du profil. */
function insertIntermediatePoint(profile: ProfilePoint[]): ProfilePoint[] {
  if (profile.length < 2) {
    return profile;
  }
  let widest = 0;
  for (let index = 1; index < profile.length; index += 1) {
    const span = profile[index].chainage_m - profile[index - 1].chainage_m;
    const currentSpan = profile[widest + 1].chainage_m - profile[widest].chainage_m;
    if (span > currentSpan) {
      widest = index - 1;
    }
  }
  const left = profile[widest];
  const right = profile[widest + 1];
  const inserted: ProfilePoint = {
    chainage_m: Number(((left.chainage_m + right.chainage_m) / 2).toFixed(6)),
    elevation_m: Number(((left.elevation_m + right.elevation_m) / 2).toFixed(6)),
    latitude: null,
    longitude: null,
  };
  return [...profile.slice(0, widest + 1), inserted, ...profile.slice(widest + 1)];
}

function replaceAt<T>(items: T[], index: number, patch: Partial<T>): T[] {
  return items.map((item, current) => (current === index ? { ...item, ...patch } : item));
}

function number(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function text(value: number | null): string {
  return value === null ? "" : String(Number(value.toPrecision(12)));
}

function scale(value: number | null, factor: number): number | null {
  return value === null ? null : value * factor;
}

function unscale(value: number | null, factor: number): number | null {
  return value === null ? null : value / factor;
}

function formatLength(lengthM: number): string {
  return lengthM >= 1000 ? `${(lengthM / 1000).toFixed(3)} km` : `${lengthM.toFixed(1)} m`;
}
