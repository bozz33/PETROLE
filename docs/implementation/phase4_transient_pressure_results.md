# P4-F — Résultats transitoires P(x,t)

Références : D07 charge totale et contrat Phase 4 H(x,t), Q(x,t), P(x,t).

Le solveur MOC produit déjà H et Q. La pression est reconstruite uniquement lorsque les données nécessaires à l’inversion de la relation D07 sont fournies explicitement :

`H = z + p/(ρg) + αv²/(2g)` avec `v = 4Q/(πD²)`.

`build_transient_pressure_snapshots` reçoit, pour chaque snapshot et chaque nœud, l’élévation, le diamètre, la densité et le coefficient cinétique. La densité est volontairement autorisée à varier dans le temps afin de ne pas supposer un produit constant pendant un scénario multiproduit.

`build_transient_pressure_envelopes` publie ensuite les pressions minimale et maximale observées par nœud, leurs instants et le nombre d’états donnant une pression absolue calculée négative.

Une pression négative n’est jamais rabattue à zéro et n’est pas automatiquement qualifiée comme un résultat physique valide : elle reste signalée pour les futurs modèles spécifiques de cavitation/séparation de colonne et leurs benchmarks. Cette brique n’ajoute donc aucun modèle de cavitation, aucune enveloppe MAOP réglementaire et aucune validation industrielle.
