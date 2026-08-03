# Prompt de reprise sur le VPS

Copier le texte suivant dans la nouvelle session après connexion au VPS :

```text
Continue le développement du projet PETROLE depuis /opt/petrole.

Parle-moi en français. Dans le code et la documentation, utilise un français professionnel,
précis et naturel. Aucun texte produit, commentaire, commit ou document ne doit mentionner un
outil de génération ni présenter le travail comme automatisé.

Avant toute modification :
1. lis entièrement /opt/petrole/MEMOIRE_PROJET.md ;
2. lis /opt/petrole/deployment/VPS.md ;
3. lis les documents de qualification dans /opt/petrole/docs/validation/ ;
4. vérifie l'état réel avec git status, git log, git worktree list, Docker Compose,
   var/vps/deployment-state.json et /api/v1/health/ready ;
5. identifie la branche ou le worktree du frontend développé en parallèle.

Préserve tous les fichiers et changements existants, en particulier le frontend et
docs/charte graphique.png s'il est toujours non suivi. Ne réinitialise, ne supprime et
n'écrase aucun travail non commité. Travaille sur une branche dédiée si plusieurs chantiers
coexistent.

GitHub Actions est indisponible pour quota. Utilise les tests locaux/VPS comme preuve : lance
deployment/scripts/vps/qualify.sh, conserve les résultats sous var/validation-vps, corrige les
erreurs réelles de Trivy ou ZAP, valide la charge, le HTTPS, les workflows, la sauvegarde et la
restauration. Vérifie aussi un redémarrage contrôlé du VPS.

Priorité : terminer et qualifier le backend MVP avant de déclarer le frontend livré. Ferme les
écarts MUST prouvés par le code et les tests, sans revendiquer de conformité réglementaire
complète tant que les textes officiels applicables, les données industrielles et la validation
d'un ingénieur habilité manquent. Préserve l'avancement frontend et synchronise les contrats API.

Après chaque jalon : mets à jour MEMOIRE_PROJET.md avec date, commit, commandes de test,
résultats et limites restantes. Effectue un commit clair et pousse seulement après validation.
Commence par me donner un état court, fondé sur les vérifications réelles, puis continue le
travail sans repartir de zéro.
```
