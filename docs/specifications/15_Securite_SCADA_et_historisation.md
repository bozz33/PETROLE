Plateforme de transport et de stockage des hydrocarbures

D15

Sécurité, SCADA et historisation

Architecture OT/IT, protocoles, cybersécurité, qualité des données et continuité

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D15 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Principes

- Architecture zones/conduits

- Modèle de menace

- Identités

- Réseau

- Connecteurs

- OPC UA

- Historian

- Qualité temporelle

- Alarmes

- Sauvegarde

- Incident

- Exigences MVP

- Feuille de route

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Principes

| Principe de sécurité Le MVP n’écrit jamais dans le SCADA, le PLC, le RTU, le SIS ou l’ESD. Les données industrielles sont lues via une passerelle isolée et répliquées vers la plateforme. |



- Séparation des réseaux OT, DMZ industrielle et IT.

- Moindre privilège, comptes de service dédiés et certificats.

- Aucune dépendance Internet obligatoire sur le site.

- Traçabilité des données de la source jusqu’au calcul.

- Synchronisation temporelle et codes qualité obligatoires.

- Défense en profondeur inspirée d’IEC 62443.

- Les fonctions de sécurité instrumentée restent dans les systèmes certifiés.

# 2. Architecture de zones et conduits

| Zone | Contenu | Flux autorisés |

| Zone terrain | Capteurs, actionneurs, PLC, RTU | Vers contrôle selon architecture opérateur |

| Zone contrôle | SCADA/HMI, serveurs temps réel | Flux nécessaires vers DMZ |

| SIS/ESD | Systèmes de sécurité | Aucun accès direct depuis la plateforme |

| DMZ industrielle | OPC proxy, réplication historian, bastion | Flux filtrés et unidirectionnels si possible |

| Zone analytique locale | Passerelle de la plateforme et cache | Lecture depuis DMZ, envoi contrôlé vers serveur |

| Zone application | API, worker, base, frontend | Aucun accès direct au PLC |

| Zone utilisateurs | Navigateurs et postes ingénieurs | HTTPS vers application |

| Cloud futur | Services autorisés | VPN/liaison chiffrée et politique de données |



# 3. Modèle de menace synthétique

| Menace | Impact | Mesures |

| Compte compromis | Accès aux projets/données | MFA admin, RBAC, session, audit |

| API vulnérable | Exfiltration ou modification | Validation, authz, rate limit, tests OWASP |

| Dépendance compromise | Code malveillant | SBOM, pinning, scan, revue |

| Passerelle OT compromise | Pivot vers contrôle | DMZ, lecture seule, allow-list, durcissement |

| Données falsifiées | Mauvaise décision | Signature/hash, qualité, comparaison physique |

| Horloge désynchronisée | Erreur de bilan/fuite | NTP/PTP surveillé, timestamps doubles |

| Ransomware | Indisponibilité/perte | Sauvegardes hors ligne, restauration testée |

| Déni de service calcul | Saturation CPU/files | Quotas, file, limites et priorités |

| Rapport falsifié | Décision non traçable | Hash, signature/approbation, audit |



# 4. Identités et secrets

- Comptes nominatifs pour les humains ; comptes de service pour les connecteurs.

- MFA obligatoire pour administrateurs avant le pilote.

- OIDC/annuaire d’entreprise privilégié lors d’un déploiement industriel.

- Certificats OPC UA gérés avec liste de confiance et révocation.

- Secrets stockés dans un secret manager ou fichiers chiffrés, jamais dans Git.

- Rotation documentée des clés, mots de passe et certificats.

- Scopes minimaux : un connecteur ne peut pas administrer les projets.

# 5. Sécurité réseau et hôte

| Contrôle | MVP/Pilote |

| TLS | Obligatoire pour web/API ; certificats internes ou publics |

| Pare-feu | Allow-list des flux et ports |

| Durcissement | Images minimales, utilisateur non root, patching |

| Segmentation | Base non exposée aux utilisateurs ; worker séparé |

| Accès administration | VPN/bastion et journalisation |

| Sortie Internet | Interdite ou proxifiée selon site |

| Antimalware/EDR | Selon politique de l’opérateur |

| Scan conteneur | À chaque build/release |

| Rate limiting | Authentification, uploads et calculs |



# 6. Connecteurs et passerelle industrielle

| Fonction | Exigence |

| Configuration | Tags, unités, fréquence et qualité validés avant activation |

| Lecture seule | Aucune méthode write/call vers les actifs |

| Buffer local | Résister aux coupures sans perdre l’ordre |

| Déduplication | Sequence/checkpoint et idempotence |

| Normalisation | Conversion SI après conservation brute |

| Supervision | État de connexion, latence, pertes et certificat |

| Mise à jour | Procédure contrôlée et rollback |

| Audit | Qui a modifié la configuration et quand |

| Fail-safe | Arrêt du connecteur sans impact sur le contrôle du procédé |



# 7. OPC UA

| Élément | Décision |

| Mode | Client OPC UA de la passerelle vers serveur/proxy opérateur |

| Sécurité | SignAndEncrypt, politique approuvée, certificats |

| Découverte | Configuration contrôlée, pas de découverte non filtrée en production |

| Souscriptions | Sampling et publishing adaptés au besoin, files dimensionnées |

| Qualité | Conserver StatusCode complet ou mapping réversible |

| Horodatage | SourceTimestamp et ServerTimestamp |

| Reconnexion | Backoff, reprise et indication de trou |

| Namespaces | URI et NodeId, ne pas dépendre seulement d’un index numérique |

| Historique | Préférer historian/réplication plutôt que surcharge du serveur temps réel |



# 8. Historisation

| Phase | Solution | Critère de passage |

| MVP | PostgreSQL partitionné | Données de démonstration et imports limités |

| Pilote | PostgreSQL/TimescaleDB selon benchmark | Volume de tags et requêtes connu |

| Multi-sites | TimescaleDB ou Apache IoTDB | Débit d’ingestion, compression et edge-cloud |

| Intégration opérateur | Lecture de l’historian existant | Éviter la duplication inutile |



La plateforme ne cherche pas à remplacer immédiatement l’historian industriel. Elle peut conserver un sous-ensemble analytique, les données nécessaires aux calculs et les résultats dérivés, tout en gardant une référence vers la source officielle.

# 9. Qualité temporelle et des mesures

| Contrôle | Indicateur |

| Synchronisation | Offset horloge par source |

| Latence | ingest_ts - source_ts |

| Complétude | Échantillons reçus/attendus |

| Ordre | Séquences hors ordre |

| Qualité | Pourcentage good/uncertain/bad |

| Stagnation | Durée sans variation significative |

| Sauts | Variation au-delà de la physique/plage |

| Biais | Écart persistant au modèle ou capteur redondant |

| Calibration | Date d’échéance et statut |



# 10. Alarmes et événements

- La plateforme importe les alarmes sans devenir le système maître de gestion des alarmes.

- Chaque événement conserve source, priorité, état, acquittement et chronologie si disponible.

- Les alertes analytiques sont clairement distinguées des alarmes de contrôle.

- Les seuils analytiques sont versionnés et leurs faux positifs suivis.

- Les principes ISA-18.2/IEC 62682 guident la rationalisation future.

- Une alerte de fuite reste une suspicion nécessitant une procédure opérateur.

# 11. Sauvegarde, reprise et continuité

| Élément | Plan |

| PostgreSQL | Sauvegarde complète + WAL selon criticité future |

| Stockage objet | Versioning ou sauvegarde séparée |

| Configurations | Git privé + sauvegarde des secrets séparée |

| Certificats | Inventaire, sauvegarde chiffrée et procédures de remplacement |

| Passerelle | Image/configuration reproductible ; cache rejouable |

| Tests | Restauration trimestrielle au pilote, plus fréquente en production |

| Mode dégradé | La perte de la plateforme ne doit pas arrêter le procédé |



# 12. Réponse aux incidents

| Phase | Actions |

| Détecter | Alertes, logs, EDR, anomalies et signalement utilisateur |

| Contenir | Révoquer compte/certificat, isoler service, préserver OT |

| Préserver | Logs, snapshots, hashes et chronologie |

| Éradiquer | Corriger vulnérabilité et dépendances |

| Restaurer | Depuis sauvegarde vérifiée, surveiller |

| Apprendre | Post-mortem sans blâme, actions et mise à jour des risques |

| Notifier | Selon contrat, réglementation et responsable de traitement |



# 13. Exigences de sortie MVP

- Application HTTPS, RBAC, audit et sauvegarde.

- Aucun endpoint de commande industrielle.

- Imports historiques par fichiers avec codes qualité.

- Architecture documentée pour une passerelle OPC UA future.

- Scan de dépendances et images en CI.

- Test de restauration réussi.

- Journal scientifique distinct et corrélation de bout en bout.

- Checklist de sécurité avant démonstration ou pilote.

# 14. Feuille de route OT

| Étape | Livrable |

| OT-0 | Atelier avec l’opérateur : architecture, protocoles, politiques |

| OT-1 | POC hors ligne sur simulateur OPC UA |

| OT-2 | Passerelle en laboratoire et tests de sécurité |

| OT-3 | Connexion à une réplique/historian de test |

| OT-4 | Pilote en lecture seule en DMZ |

| OT-5 | Qualification disponibilité et données |

| OT-6 | RTTM et analytics quasi temps réel |

| OT-7 | Toute interaction de contrôle fait l’objet d’un projet séparé IEC 61511/62443 |



# Sources et références

- IEC 62443 pour la cybersécurité industrielle.

- IEC 61511 pour la séparation et le cycle de vie de la sécurité instrumentée.

- IEC 62541 pour OPC UA et ISA-18.2/IEC 62682 pour les alarmes.

- D11 à D14 pour architecture, données, API et licences.

Fin du document