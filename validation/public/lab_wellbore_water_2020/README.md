# LAB-WELLBORE-WATER-2020 — benchmark prédictif de soutien

## Source primaire

Raj Kiran et al., *Wellbore fluid sonic conditions during blowouts*, **Journal of Petroleum Science and Engineering 195 (2020), 107822**, DOI `10.1016/j.petrol.2020.107822`.

Avant la campagne multiphasique, les auteurs qualifient leur installation avec un écoulement **monophasique d'eau**. La section de test verticale a un diamètre publié de 83 mm et une longueur de 5,5 m. La Table 1 publie quatre points de débit avec la perte de pression frictionnelle mesurée et la prédiction utilisée par les auteurs.

`single_phase_water_table1.csv` conserve ces quatre points.

## Intérêt pour PETROLE

Le tableau fournit une vérité indépendante `ΔP_friction(Q)` et peut servir de benchmark de soutien des pertes de charge dans une conduite lisse. Il est intéressant pour vérifier la tendance et l'ordre de grandeur en régime turbulent.

## Limite de classification

Ce cas **ne compte pas** parmi les trois validations terrain strictes de PUBLIC-VALIDATION-02 :

- la grandeur tabulée est la composante de perte frictionnelle de la section verticale, pas une paire complète de pressions absolues d'extrémité ;
- l'état thermophysique précis de l'eau et la rugosité exacte ne sont pas complètement tabulés dans les informations publiques consultées ;
- convertir le cas en une conduite horizontale équivalente pour fournir `ΔP_friction` comme condition de bord serait une transformation de benchmark, pas un rejeu brut de l'installation.

Statut : `SUPPORTING_ONLY`. Toute exécution PETROLE doit publier ces transformations et garder `predictive_validation_verdict` distinct du statut de fermeture terrain.
