# Requalification consolidée du backend MVP — 3 août 2026

## Verdict de livraison

Le backend remplit le périmètre **MVP logiciel** défini par les exigences MUST de
`D04` : calcul hydraulique liquide stationnaire, stations/pompes, transferts de
réservoirs, import, rapports, organisations, rôles, audit, tâches asynchrones,
persistance et déploiement conteneurisé. La recette Docker finale est verte.

Cela ne signifie pas « certifié industriel à 100 % ». Une certification ASME, API
ou ISO, une autorisation d'exploiter et une validation sur réseau opérateur réel
restent des décisions humaines et contractuelles externes au logiciel. Les limites
ci-dessous font partie du verdict, pas des réserves cachées.

## Preuves de recette exécutées

| Contrôle | Résultat vérifié |
|---|---:|
| Recette complète backend Docker | **485 tests réussis** en 134,46 s |
| Formatage Ruff | 122 fichiers déjà formatés |
| Analyse Ruff | aucune alerte |
| Mypy | 91 fichiers sources, aucune erreur |
| `pip check` | aucune dépendance incohérente |
| Validation scientifique | **41/41** cas réussis |
| Empreinte de la preuve scientifique | `b476c957ada65949331d87398677f8b0cd1509784c38ed5509c45105d046dbd9` |
| Test de santé et en-têtes HTTP | API locale `200`, corrélation et en-têtes de défense présents |
| Build web production | TypeScript et Vite réussis ; configuration Nginx valide dans le réseau Compose |
| Images API et worker production | construites depuis le code final ; import applicatif réussi |

Le rapport JUnit, les rapports scientifiques, les audits et les scans sont conservés
hors Git dans `var/validation-current/`, car ils dépendent de la machine et de la
date de la campagne.

## Performance et calcul scientifique

La correction du parcours hydraulique évite les balayages quadratiques du profil et
des tronçons. Elle conserve les conventions de frontière et des replis défensifs
pour les profils non ordonnés.

| Essai | Résultat le plus récent |
|---|---:|
| P95, 20 calculs, réseau de 1 000 tronçons | 0,336079 s |
| Réseau de 10 000 tronçons | 14,463021 s ; 22,819 Mio |
| 100 configurations simples | 1,397074 s |
| Rapport, 1 000 tronçons | 2,690416 s ; 190 575 octets ; 30 pages |
| Import PostgreSQL d'un million de lignes | 273,0458 s ; rejeu idempotent 0,00609 s |
| Concurrence worker | 8 prétendants, exactement une prise de job ; reprise d'un job périmé vérifiée |

Les 41 cas scientifiques incluent les comparaisons pandapipes/STANET/OpenModelica
et le cas de pompe DWSIM U03 déjà décrits dans la qualification historique. Le cas
STANET `water_one_pipe1` conserve un écart de 24,89 % dans une zone de transition
vers `Re = 2 630`, explicitement toléré et expliqué par le changement de régime ;
il ne prouve pas une équivalence fine dans cette zone. Les autres écarts restent
sous 0,051 %.

## Sécurité et conteneurs

| Contrôle | Résultat |
|---|---:|
| Gitleaks | 15 commits et l'arborescence actuelle : aucun secret détecté |
| `npm audit --audit-level=high` | 0 vulnérabilité |
| Bandit, `apps` et `packages` | 0 alerte |
| pip-audit, image API de production | aucune vulnérabilité connue ; paquet local `hydro-platform` non publié sur PyPI, donc non corrélable par cet outil |
| Trivy API | 0 vulnérabilité HIGH/CRITICAL non corrigée |
| Trivy worker | 0 vulnérabilité HIGH/CRITICAL non corrigée |
| Trivy web | 0 vulnérabilité HIGH/CRITICAL non corrigée |
| ZAP baseline local, API Compose | 0 FAIL ; un avertissement de cache volontaire |

Les images API/worker utilisent `pip 26.1.2` et ne conservent pas `setuptools` dans
le runtime. L'image web est épinglée au digest Nginx Alpine
`sha256:4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752`,
qualifié à la date de la campagne.

L'API définit `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` et
`Cross-Origin-Resource-Policy: same-origin`, y compris sur les erreurs. L'unique
avertissement ZAP « Non-Storable Content » est attendu : une API contenant des
données d'exploitation et d'authentification ne doit pas être mémorisée par un
navigateur ou un proxy partagé.

La passe ZAP est un contrôle passif local, sans TLS public et avec l'authentification
de développement désactivée. Elle ne remplace donc ni un pentest externe, ni une
revue de la configuration TLS, des secrets et des droits du déploiement cible.

## Référentiels officiels vérifiés

- [ASME B31.4-2025](https://www.asme.org/codes-standards/find-codes-standards/b31-4-pipeline-transportation-systems-liquids-slurries/2025/pdf)
  couvre notamment conception, construction, inspection, essais, exploitation et
  maintenance des conduites de liquides et boues ;
- [ISO 13623:2017](https://www.iso.org/standard/61251.html) est confirmée en 2026
  et son amendement [ISO 13623:2017/Amd 1:2024](https://www.iso.org/standard/83015.html)
  concerne les fluides contenant CO₂ ou hydrogène ;
- [API 650, 14e édition](https://www.api.org/products-and-services/api-monogram-and-apiqr/latest-updates)
  a été publiée en août 2025 ; son entrée en vigueur pour le programme Monogram est
  indiquée au 1er mars 2026.

La plateforme fournit la traçabilité nécessaire pour relier une règle, sa version,
sa preuve et une décision. Elle **n'est pas déclarée conforme** à ces textes : les
copies sous licence, une matrice clause-par-clause approuvée et la validation d'un
ingénieur compétent sont indispensables avant toute déclaration de conformité.

## Frontière du MVP et travaux externes

Les cas d'usage MVP `UC-001` à `UC-013` sont couverts par la recette. Les scénarios
avancés de `D06` restent correctement hors de cette déclaration lorsqu'ils dépassent
le MVP stationnaire : transitoires/coup de bélier, multiphasique, thermique détaillé,
batching multi-produit, détection certifiée de fuite, alignement automatique des
vannes, mouvements simultanés, estimation automatique sans débitmètre et contrôle
automatique d'évent/soupape.

Avant un pilote industriel, il faut encore :

1. acquérir les textes applicables et faire approuver la matrice normative ;
2. comparer un jeu opérateur anonymisé et autorisé, ou des mesures terrain, aux
   résultats de la plateforme ;
3. réaliser pentest, recette TLS/secrets et test de reprise sur l'infrastructure
   de production cible ;
4. définir avec l'exploitant les scénarios avancés réellement requis par le pilote.

Il est impossible de prouver « tous les workflows » ou « toutes les pannes » d'un
système ouvert. Le livrable prouve un catalogue fini de comportements, des entrées
invalides, des pannes de dépendances, de la concurrence et une recette reproductible ;
il ne doit pas être présenté autrement.
