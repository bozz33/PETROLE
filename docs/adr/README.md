# Registre des décisions d'architecture (ADR)

Ce registre reprend les décisions structurantes de la documentation officielle
(*Documentation complète du MVP v2.0*, annexe E, et D11 § 12). Chaque décision est
figée ici pour que le code puisse y faire référence explicitement.

| ADR | Décision | Statut |
| --- | --- | --- |
| [ADR-001](adr-001-monolithe-modulaire.md) | Monolithe modulaire au MVP | Acceptée |
| [ADR-002](adr-002-python-fastapi.md) | Python + FastAPI comme socle permanent | Acceptée |
| [ADR-003](adr-003-moteurs-derriere-interfaces.md) | Moteurs scientifiques derrière une interface commune | Acceptée |
| [ADR-004](adr-004-postgresql-postgis.md) | PostgreSQL/PostGIS comme source de vérité | Acceptée |
| [ADR-005](adr-005-si-interne.md) | Système SI en interne, unités d'affichage converties | Acceptée |
| [ADR-006](adr-006-shadcn-admin.md) | Shadcn Admin comme base d'interface | Acceptée |
| [ADR-007](adr-007-dwsim-externe.md) | DWSIM utilisé comme référence externe uniquement | Acceptée |
| [ADR-008](adr-008-idaes-apres-mvp.md) | IDAES reporté après le MVP | Acceptée |
| [ADR-009](adr-009-lecture-seule-avant-controle.md) | Lecture seule avant toute commande | Acceptée |
| [ADR-010](adr-010-normes-non-codees-en-dur.md) | Règles normatives versionnées, non codées en dur | Acceptée |

## Décisions moteur (DEC-*)

| ID | Décision |
| --- | --- |
| DEC-ARCH-001 | Backend central Python/FastAPI conservé du MVP au produit final. |
| DEC-ENGINE-001 | `HydroLiquid Core` est le moteur liquide principal (NumPy, SciPy, `fluids`, CoolProp, Pint + extensions métier). |
| DEC-ENGINE-002 | `pandapipes` est intégré par adaptateur après preuve de concept, jamais comme dépendance unique. |
| DEC-ENGINE-003 | Pyomo est le moteur d'optimisation ; l'énumération filtrée reste possible pour les petits cas. |
| DEC-UI-001 | Shadcn Admin sert de base visuelle ; les pages de démonstration sont remplacées. |
| DEC-SRC-001 | Les documents fournis alimentent équations et cas de validation, sans se substituer aux normes. |
| DEC-SAFETY-001 | Le MVP est un outil d'analyse : aucune commande directe d'automate, PLC ou SIS. |
