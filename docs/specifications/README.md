# Documentation de référence du projet

Ce dossier contient la documentation officielle qui pilote le développement. Toute
implémentation doit s'y conformer ; en cas de contradiction, la
**Documentation complète du MVP v2.0** fait foi.

## Document maître

| Fichier | Contenu |
| --- | --- |
| [`Documentation_complete_MVP_Plateforme_Hydrocarbures_v2.0.md`](Documentation_complete_MVP_Plateforme_Hydrocarbures_v2.0.md) | Base approuvée pour le démarrage du développement : périmètre, référentiel scientifique, architecture, API, frontend, validation, critères de réception. |

## Dossier documentaire D00 – D20

| Code | Document |
| --- | --- |
| D00 | [Index du dossier documentaire](00_Index_du_dossier_documentaire.md) |
| D01 | [Document de cadrage officiel et plan directeur](01_Document_de_cadrage_officiel_et_plan_directeur.md) |
| D02 | [Vision produit et proposition de valeur](02_Vision_produit_et_proposition_de_valeur.md) |
| D03 | [Cartographie des acteurs et processus métier](03_Cartographie_des_acteurs_et_processus_metier.md) |
| D04 | [Cahier des charges fonctionnel complet](04_Cahier_des_charges_fonctionnel_complet.md) |
| D05 | [Exigences non fonctionnelles](05_Exigences_non_fonctionnelles.md) |
| D06 | [Catalogue des cas d'usage et scénarios](06_Catalogue_des_cas_d_usage_et_scenarios.md) |
| D07 | [Référentiel scientifique et mathématique](07_Referentiel_scientifique_et_mathematique.md) |
| D08 | [Référentiel normatif international](08_Referentiel_normatif_international.md) |
| D09 | [Dictionnaire des données](09_Dictionnaire_des_donnees.md) |
| D10 | [Plan de validation scientifique](10_Plan_de_validation_scientifique.md) |
| D11 | [Architecture logicielle détaillée](11_Architecture_logicielle_detaillee.md) |
| D12 | [Modèle conceptuel et logique des données](12_Modele_conceptuel_et_logique_des_donnees.md) |
| D13 | [Spécification des API et intégrations](13_Specification_des_API_et_integrations.md) |
| D14 | [Stratégie open source et licences](14_Strategie_open_source_et_licences.md) |
| D15 | [Sécurité SCADA et historisation](15_Securite_SCADA_et_historisation.md) |
| D16 | [Plan de développement du MVP](16_Plan_de_developpement_du_MVP.md) |
| D17 | [Roadmap complète jusqu'au produit final](17_Roadmap_complete_jusqu_au_produit_final.md) |
| D18 | [Plan de tests, qualité et CI/CD](18_Plan_de_tests_qualite_et_CI_CD.md) |
| D19 | [Modèles de rapports et interfaces](19_Modeles_de_rapports_et_interfaces.md) |
| D20 | [Dossier pilote et protocole de validation industrielle](20_Dossier_pilote_et_protocole_de_validation_industrielle.md) |

Les fichiers Word d'origine sont conservés dans [`source/`](source/). Les versions Markdown
en sont une extraction destinée à la lecture, à la recherche et au suivi des différences ;
**le document Word reste la version de référence**.

## Sources non redistribuées

Le dossier de travail du porteur de projet contient également des ouvrages académiques
tiers sous droits (supports russes de modélisation, de stockage et de transport gazier) ainsi
qu'un programme d'étudiant. Ces fichiers **ne sont pas versionnés** dans ce dépôt.

Leur apport est intégré de façon indirecte et traçable :

- les équations et méthodes en sont extraites, comparées aux références internationales et
  documentées dans le code (D07, DEC-SRC-001) ;
- le cas de l'oléoduc de 460 km sert de **benchmark académique** reconstruit dans
  [`datasets/reference_cases/`](../../datasets/reference_cases/), après correction des
  erreurs identifiées dans le prototype (D10 § 5) ;
- aucun texte protégé n'est reproduit.

## Avertissement

Ces documents structurent la conception du logiciel. Ils ne remplacent ni les textes
normatifs officiels achetés auprès de leurs éditeurs, ni la validation d'un ingénieur
habilité, ni une étude de dangers, ni une autorisation réglementaire ou une certification de
site.
