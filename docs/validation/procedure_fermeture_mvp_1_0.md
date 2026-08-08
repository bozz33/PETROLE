# Procédure de fermeture — PETROLE MVP 1.0

## But

Cette procédure ferme les dernières portes du cahier des charges fonctionnel
D04 sans étendre le périmètre du produit. Les fonctions F01 à F07 sont déjà
développées ; il reste à produire les preuves de recette sur le candidat final,
puis à obtenir l'acceptation d'un ingénieur métier extérieur à l'équipe.

## Branche de travail

Les derniers compléments de fermeture sont développés sur :

`feat/mvp-final-closure`

Aucun tag `v1.0.0-mvp` ne doit être créé avant la fin de cette procédure.

## 1. Préparer le dossier de référence

Sur une instance de recette propre, créer les deux comptes séparés :

- Engineer ;
- Approver.

Monter le dossier de référence avec le script existant :

```bash
python deployment/scripts/vps/projet_reference.py \
  --base-url https://petrole.distesage.com/api/v1 \
  --email "$RECETTE_ENGINEER_EMAIL" \
  --password "$RECETTE_ENGINEER_PASSWORD" \
  --approver-email "$RECETTE_APPROVER_EMAIL" \
  --approver-password "$RECETTE_APPROVER_PASSWORD"
```

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

## 3. Vérifier la même version local / serveur

D04 exige le déploiement de la même version sur un poste local et un serveur de
test. Démarrer localement exactement le même commit et relancer :

```bash
python deployment/scripts/vps/recette_mvp_finale.py \
  --base-url https://petrole.distesage.com/api/v1 \
  --email "$RECETTE_ENGINEER_EMAIL" \
  --password "$RECETTE_ENGINEER_PASSWORD" \
  --expected-git-sha "$(git rev-parse HEAD)" \
  --require-same-build \
  --secondary-base-url http://127.0.0.1:8000/api/v1 \
  --secondary-email "$LOCAL_ENGINEER_EMAIL" \
  --secondary-password "$LOCAL_ENGINEER_PASSWORD"
```

La recette échoue si l'API primaire ne sert pas le SHA candidat, ou si les deux
instances diffèrent sur la version applicative, le SHA Git, la version du noyau
scientifique ou la révision de migration publiés par `/api/v1/version`.

## 4. Rejouer la qualification complète sur le SHA final

Après les derniers commits et avant tout tag final :

`deployment/scripts/vps/deploy.sh` scelle l'image avec le SHA, la référence Git
et la date UTC du candidat courant. Vérifier que `GET /api/v1/version` publie ce
SHA avant de lancer cette campagne.

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

## 5. Acceptation par l'ingénieur métier

Remettre à l'ingénieur extérieur :

- le projet `REF-MVP-01` ;
- la note de calcul ;
- les exports ;
- `summary.json` et `summary.md` ;
- le rapport de qualification ;
- la fiche `docs/validation/acceptation_ingenieur_mvp.md`.

La release est bloquée tant qu'une réserve S0, S1 ou S2 reste ouverte.

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
deployment/scripts/vps/release-artifacts.sh v1.0.0-mvp
git tag -s v1.0.0-mvp -m 'PETROLE MVP 1.0 qualifié et accepté'
```

## 7. Critère de sortie

Le MVP peut être déclaré terminé uniquement lorsque :

- toutes les exigences MUST du périmètre MVP sont implémentées ;
- le dossier de référence passe les portes automatisables ;
- la qualification complète porte sur le SHA final ;
- l'ingénieur extérieur accepte le dossier sans réserve S0/S1/S2 ;
- les artefacts de release sont identifiés, hachés et signés pour une diffusion à un tiers ;
- le tag final pointe exactement sur le commit qualifié et accepté.

La mention à utiliser est alors :

> **PETROLE MVP 1.0 — MVP logiciel terminé, qualifié et accepté sur son périmètre défini.**

Cette mention ne vaut pas certification industrielle ni autorisation d'exploiter
un site réel.
