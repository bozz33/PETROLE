# Jeux de référence scientifiques

Ce dossier reçoit les entrées externes figées et leurs résultats attendus : cas académiques,
calculs manuels approuvés, comparaisons pandapipes ou DWSIM et données de pilote autorisées.

La première porte de réception est directement exécutable dans
`packages/validation/hydro_validation/mvp_cases.py`. Elle couvre `V-001` à `V-020`, y compris
le benchmark de 460 km. Les familles analytiques détaillées restent dans
`packages/validation/hydro_validation/cases.py`.

Toute nouvelle donnée placée ici doit fournir :

- un identifiant stable et une version ;
- la source et la méthode de référence ;
- les unités SI des entrées et sorties ;
- les valeurs attendues et leur tolérance par grandeur ;
- une empreinte SHA-256 lorsque la donnée provient d'un fichier externe ;
- la décision de revue scientifique ayant autorisé son emploi.

Les rapports générés par `hydro-validate` sont des preuves d'exécution. Ils sont écrits sous
`var/validation/` et ne remplacent pas les données de référence versionnées.
