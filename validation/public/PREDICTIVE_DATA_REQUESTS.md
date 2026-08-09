# PUBLIC-VALIDATION-02 — demandes de données pour lever les blocages

Ce document décrit uniquement les données nécessaires à une validation prédictive indépendante. Il ne constitue pas une demande de données sensibles d'exploitation au-delà de ce qu'un auteur ou exploitant est autorisé à partager. Des séries anonymisées et décalées temporellement conviennent si les grandeurs hydrauliques restent cohérentes.

## FIELD-GUANGDONG-NO1-2021 — priorité 1

Source : Wang et al., Energies 2021, DOI `10.3390/en14185871`.

La publication indique que les données sont disponibles sur demande auprès de l'auteur correspondant mais non publiques à cause d'une restriction du financeur.

Demander pour **Pipeline No.1 sans drag reducer**, idéalement 50 à 500 points stabilisés :

- timestamp ou identifiant de régime anonymisé ;
- produit (`gasoline` / `diesel`) ou composition de batch ;
- pression amont et aval, avec indication gauge/absolute et unité ;
- débit mesuré et type de débitmètre ;
- densité mesurée ou utilisée ;
- température amont/aval si disponible ;
- état des pompes/vannes si cela affecte la section ;
- incertitudes ou classe métrologique si partageables.

Les débits seront masqués au solveur PETROLE et utilisés uniquement après calcul comme vérité indépendante.

## FIELD-BN1-2022 — priorité 2

Source : Wei et al., Energies 2022, DOI `10.3390/en15165880`.

L'article annonce 2791 enregistrements réels et publie un échantillon.

Demander :

- les 2791 lignes ou un sous-ensemble représentatif ;
- altitude B et N1 ou différence d'altitude hydraulique ;
- confirmation de l'interprétation de `φ529×7 mm` et du diamètre intérieur ;
- viscosité cinématique/dynamique en fonction de la température, ou analyses labo du brut ;
- si disponible, pression finale mesurée séparément plutôt que seulement `ΔP` ;
- incertitudes instrumentales.

Aucune relation `nu(T)` ne sera ajustée sur le jeu de validation lui-même. Si une calibration est nécessaire, elle doit utiliser une série A distincte et geler les paramètres avant la série B.

## FIELD-EAST-CHINA-2025 / EC-03 — priorité 3

Source : Wang et al., Processes 2025, DOI `10.3390/pr13082459`.

Demander pour le point de contrôle et, si possible, plusieurs régimes du tronçon `Pigging Station 2 → Pumping Station 2` :

- pressions numériques synchronisées aux extrémités ;
- référence gauge/absolute ;
- timestamps ;
- débit débitmètre correspondant ;
- température ;
- rugosité ou information de conduite disponible ;
- incertitudes des capteurs.

Le débit de 270 m3/h déjà publié restera hors des entrées lorsque EC-03 sera exécuté.

## FIELD-QINGTIE-2022 — à rouvrir avec la phase thermique

Sources : Qingtie Fourth-Line, notamment DOI `10.3390/en15207453` et `10.1002/ese3.795`.

Demander :

- chainage et altitude des neuf stations ;
- diamètre intérieur et rugosité par section ;
- `rho(T)` et `mu(T)` / `nu(T)` du brut ;
- pressions, températures et débits synchronisés ;
- configuration et caractéristiques des pompes ;
- métadonnées de chauffage et température sol si le solveur thermique est utilisé.

Ce cas ne doit pas être traité comme validation du moteur isotherme actuel.

## Règle de confidentialité

Une validation PETROLE n'exige pas l'identité de l'installation ni un historique SCADA complet. Un exploitant peut fournir un extrait anonymisé avec distances relatives, altitudes relatives, propriétés du fluide, pressions et débits, à condition que les transformations soient documentées et ne modifient pas la physique du cas.
