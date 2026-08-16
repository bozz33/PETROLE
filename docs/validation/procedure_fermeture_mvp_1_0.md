# Procédure de fermeture — PETROLE MVP 1.0

## But

Cette procédure ferme les dernières portes du cahier des charges fonctionnel
D04 sans étendre le périmètre du produit. Le déploiement cible du MVP est
**mono-organisation et mono-utilisateur** : l'ingénieur utilisateur prépare,
calcule, analyse et documente directement ses études.

Le workflow historique Engineer → Approver est désactivé dans ce périmètre. Il
ne faut pas créer un second compte uniquement pour simuler une validation qui
n'existe pas dans l'usage réel.

Aucun tag `v1.0.0-mvp` ne doit être créé avant la fin de cette procédure.

## 1. Préparer le dossier de référence

Utiliser le compte de l'ingénieur utilisateur :

```bash
python deployment/scripts/vps/projet_reference_single_user.py \
  --base-url https://petrole.distesage.com/api/v1 \
  --email "$RECETTE_ENGINEER_EMAIL" \
  --password "$RECETTE_ENGINEER_PASSWORD"
```

Le script historique `projet_reference.py` reste conservé dans le dépôt pour
compatibilité avec les anciens essais multi-utilisateurs, mais il n'est plus le
point d'entrée du MVP mono-utilisateur.

Le dossier attendu contient au minimum 101 nœuds, 100 tronçons, 5 stations,
15 pompes et 10 réservoirs.

## 2. Exécuter les portes complémentaires automatisables

```bash
python deployment/scripts/vps/recette_mvp_finale.py \
  --base-url https://petrole.distesage.com/api/v1 \
  --email "$RECETTE_ENGINEER_EMAIL" \
  --password "$RECETTE_ENGINEER_PASSWORD" \
  --project-code REF-MVP-01 \
  --expected-git-sha "$(git rev-parse HEAD)"
```

Le script doit terminer avec un code retour nul et produire :

- `var/validation-vps/recette-mvp-finale/summary.json` ;
- `var/validation-vps/recette-mvp-finale/summary.md`.

Il vérifie ou exécute :

1. le SHA exact servi par l'API, la taille et la validité topologique du dossier ;
2. la baseline, les scénarios pompe indisponible, secours et débit réduit ;
3. le cinquième scénario volontairement non réalisable et son diagnostic ;
4. les imports de profil, courbe pompe, barémage et propriétés produit, avec lignage normalisé ;
5. un transfert bac-à-bac couplé à HydroLiquid et son bilan matière ;
6. une optimisation bornée, une comparaison persistée et une recommandation ;
7. la note de calcul, les rapports opérationnels et les exports XLSX, CSV et JSON.

## 3. Vérifier la même version sur deux déploiements

D04 exige de vérifier le même build sur l'instance principale et une instance
secondaire isolée. Cette seconde instance est une **preuve technique**, pas une
seconde personne ni un second rôle métier.

```bash
python deployment/scripts/vps/recette_mvp_finale.py \
  --base-url https://petrole.distesage.com/api/v1 \
  --email "$RECETTE_ENGINEER_EMAIL" \
  --password "$RECETTE_ENGINEER_PASSWORD" \
  --expected-git-sha "$(git rev-parse HEAD)" \
  --require-same-build \
  --secondary-base-url "$SECONDARY_BASE_URL" \
  --secondary-email "$SECONDARY_EMAIL" \
  --secondary-password "$SECONDARY_PASSWORD"
```

La recette échoue si l'API primaire ne sert pas le SHA candidat, ou si les deux
instances diffèrent sur la version applicative, le SHA Git, la version du noyau
scientifique ou la révision de migration publiés par `/api/v1/version`.

Pour une preuve renforcée, archiver également l'identifiant digest de l'image
API lorsque la même image binaire est utilisée sur les deux instances.

## 4. Rejouer la qualification complète sur le SHA final

Après les derniers commits et avant tout tag final, déployer le candidat et
vérifier que `GET /api/v1/version` publie son SHA exact, puis lancer :

```bash
./deployment/scripts/vps/qualify.sh production
```

Le rapport final doit mentionner le **SHA exact** ayant passé :

- tests backend ;
- validation scientifique 41/41 ;
- tests web ;
- Playwright ;
- Ruff / mypy / TypeScript / build ;
- npm audit ;
- Gitleaks ;
- Trivy ;
- OWASP ZAP ;
- sauvegarde et restauration ;
- HTTPS / readiness.

Une campagne portant sur un commit parent ne qualifie pas un HEAD ayant reçu des
modifications applicatives ultérieures.

## 5. Recette métier par l'ingénieur utilisateur

Remettre à l'ingénieur utilisateur :

- le projet `REF-MVP-01` ;
- la note de calcul ;
- les exports ;
- `summary.json` et `summary.md` ;
- le rapport de qualification ;
- la fiche `docs/validation/acceptation_ingenieur_mvp.md`.

La release est bloquée tant qu'une réserve S0, S1 ou S2 reste ouverte.

Cette recette interne ne doit pas être présentée comme une validation
indépendante. Une revue par un autre ingénieur est recommandée avant un pilote
industriel, une utilisation décisionnelle réelle ou une revendication externe
de validation.

## 6. SBOM et signature

Le script existant :

```bash
deployment/scripts/vps/release-artifacts.sh v1.0.0-mvp
```

produit les SBOM CycloneDX, les digests des images et `SHA256SUMS`.

La clé de signature doit être désignée par le mainteneur ; elle ne doit jamais
être générée ou stockée automatiquement dans le dépôt. Une fois la clé choisie :

```bash
export RELEASE_SIGNING_KEY='<identifiant-cle-gpg>'
CANDIDATE_SHA="$(git rev-parse HEAD)"
git tag -s v1.0.0-mvp "${CANDIDATE_SHA}" \
  -m 'PETROLE MVP 1.0 qualifié et accepté'
git verify-tag v1.0.0-mvp
deployment/scripts/vps/release-artifacts.sh v1.0.0-mvp
gpg --verify var/release/v1.0.0-mvp/SHA256SUMS.asc \
  var/release/v1.0.0-mvp/SHA256SUMS
git push origin v1.0.0-mvp
```

Le tag est créé localement et vérifié **avant** les SBOM : le script refuse un
tag absent, léger ou dont la signature ne peut pas être vérifiée. Le push est
volontairement la dernière étape, après vérification des empreintes et des
artefacts produits localement.

## 7. Critère de sortie

Le MVP peut être déclaré terminé uniquement lorsque :

- toutes les exigences MUST du périmètre MVP sont implémentées ;
- le dossier de référence passe les portes automatisables ;
- la qualification complète porte sur le SHA final ;
- l'ingénieur utilisateur termine la recette sans réserve S0/S1/S2 ;
- les artefacts de release sont identifiés, hachés et signés pour une diffusion à un tiers ;
- le tag final pointe exactement sur le commit qualifié et accepté.

La mention à utiliser est alors :

> **PETROLE MVP 1.0 — MVP logiciel terminé, qualifié et accepté sur son périmètre défini.**

Cette mention ne vaut pas certification industrielle, validation indépendante,
ni autorisation d'exploiter un site réel.
