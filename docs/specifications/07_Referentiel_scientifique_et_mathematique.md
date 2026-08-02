Plateforme de transport et de stockage des hydrocarbures

D07

Référentiel scientifique et mathématique

Équations, hypothèses, algorithmes et domaines de validité

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D07 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Principes scientifiques

- Unités et conventions

- Propriétés des fluides

- Écoulement liquide

- Pertes de charge

- Pompes

- Réseau et conditions aux limites

- Zones gravitaires

- Réservoirs et transferts

- Gaz

- Transitoires

- Optimisation

- Diagnostics numériques

- Registre des modèles

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Principes scientifiques

- Le moteur physique est déterministe, testable et indépendant de l’interface.

- Chaque équation doit être identifiée par un code, une source, un domaine de validité et une version.

- Les unités internes sont SI ; les unités utilisateur sont converties et conservées.

- Les valeurs par défaut, extrapolations et approximations sont signalées.

- Les règles de conformité ne doivent pas être confondues avec les équations de conservation.

- La plateforme doit refuser un résultat déclaré valide lorsque la convergence ou les bilans sont insuffisants.

# 2. Unités et conventions

| Grandeur | Symbole | Unité interne | Convention |

| Distance | x, L | m | Abscisse croissante dans le sens nominal |

| Altitude | z | m | Référence géodésique du projet |

| Débit volumique | Q | m³/s | Positif selon orientation du tronçon |

| Débit massique | ṁ | kg/s | ṁ = ρQ |

| Pression | p | Pa absolu | Les pressions manométriques sont explicitement marquées |

| Charge | H | m de fluide | Charge totale selon Bernoulli |

| Densité | ρ | kg/m³ | Fonction éventuelle de T et p |

| Viscosité dynamique | μ | Pa·s | μ = ρν |

| Viscosité cinématique | ν | m²/s | Fonction de la température |

| Température | T | K | Affichage possible en °C |

| Puissance | P | W | Électrique ou hydraulique identifiée |

| Énergie | E | J ou kWh | Unité d’affichage paramétrable |



# 3. Propriétés des fluides

| ρ = f(T, p, composition) Densité déterminée par données expérimentales, corrélation ou bibliothèque de propriétés. |



| ν = f(T)  ;  μ = ρν La viscosité doit être évaluée à la température locale du calcul. |



| p_v = f(T) Pression de vapeur utilisée pour les contrôles de cavitation et de séparation de phase. |



Pour les produits pétroliers réels, les tables de laboratoire ou de l’opérateur sont prioritaires. Les corrélations académiques peuvent compléter les données mais leur domaine de validité doit être explicite. Pour un fluide non newtonien ou un produit proche du point d’écoulement, un modèle rhéologique spécifique est requis.

| Modèle de propriété | Usage | Contrôles |

| Table interpolée | Produits réels | Monotonie, bornes, unité et source |

| Corrélation paramétrique | Études et extrapolation contrôlée | Erreur d’ajustement et domaine |

| CoolProp/équation d’état | Fluides couverts par la bibliothèque | Fluide, backend et version |

| Valeur constante | Cas pédagogique ou plage étroite | Avertissement si T/p varient fortement |



# 4. Équations de base pour liquides

| H = z + p/(ρg) + αv²/(2g) Charge totale dans une section ; α est le coefficient de correction cinétique. |



| v = 4Q/(πD²) Vitesse moyenne dans une conduite circulaire pleine. |



| Re = ρvD/μ = vD/ν Nombre de Reynolds pour déterminer le régime et le facteur de frottement. |



| H₁ - H₂ = h_f + h_m - H_p + H_t Bilan de charge : pertes linéaires et singulières, pompes et turbines éventuelles. |



Dans le MVP, le calcul suppose un liquide monophasé, une conduite rigide, un régime permanent et une température imposée ou calculée par un modèle simplifié. Les effets transitoires sont traités dans une phase ultérieure.

# 5. Pertes de charge

| h_f = λ (L/D) v²/(2g) Darcy-Weisbach pour les pertes linéaires. |



| h_m = ΣK · v²/(2g) Pertes singulières pour vannes, coudes, filtres et accessoires. |



| 1/√λ = -2 log₁₀( ε/(3.7D) + 2.51/(Re√λ) ) Relation de Colebrook-White pour l’écoulement turbulent. |



| Régime | Méthode minimale | Remarque |

| Laminaire | λ = 64/Re | Conduite circulaire, fluide newtonien |

| Transition | Interpolation ou modèle documenté | Résultats accompagnés d’un avertissement |

| Turbulent | Colebrook-White ou approximation validée | Rugosité absolue et diamètre interne |

| Conduite vieillie | Rugosité calibrée | La calibration ne doit pas masquer une anomalie réelle |



# 6. Pompes centrifuges

| H_p(Q,N) = (N/N₀)² · H₀(Q·N₀/N) Loi d’affinité simplifiée pour variation de vitesse, dans la zone de validité du constructeur. |



| P_h = ρgQH_p  ;  P_abs = P_h/η Puissances hydraulique et absorbée. |



| NPSH_a = (p_abs,suction - p_v)/(ρg) + v_s²/(2g) NPSH disponible, comparé au NPSH requis avec marge de projet. |



| Configuration | Combinaison de courbes |

| Pompes en série | Les charges s’additionnent au même débit. |

| Pompes en parallèle | Les débits s’additionnent à la même charge. |

| Vitesse variable | Application des lois d’affinité ou carte constructeur. |

| Pompes différentes | Résolution du partage de débit et contrôle de stabilité. |



| Exigence de calcul Les points expérimentaux H(Q), η(Q), P(Q) et NPSHr(Q) restent la source principale. L’approximation polynomiale sert au calcul mais ne doit pas effacer les limites et points d’origine. |



# 7. Réseau, graphe et conditions aux limites

| Σ ṁ_entrant - Σ ṁ_sortant = 0 Conservation de masse à chaque nœud stationnaire sans stockage. |



Le réseau est représenté par un graphe orienté. Les inconnues peuvent être des pressions nodales et des débits de branches. Les conditions aux limites admises sont notamment : pression imposée, débit imposé, niveau de réservoir, demande, injection et caractéristique de pompe. Le système doit vérifier que le problème est suffisamment contraint et détecter les conditions contradictoires.

| Méthode | Usage proposé | Contrôle |

| Propagation sur réseau linéaire | Pipeline séquentiel simple | Résidu aux frontières |

| Newton-Raphson | Réseau ramifié non linéaire | Jacobienne, pas amorti, résidu |

| Dichotomie/bracketing | Débit unique avec fonction monotone | Encadrement du zéro |

| Méthode hybride | Robustesse si Newton échoue | Basculement journalisé |

| Continuation | Cas fortement non linéaire | Progression depuis un cas facile |



# 8. Zones gravitaires ou partiellement remplies

Les documents de recherche fournis décrivent un algorithme de calcul arrière et la recherche des sections où la pression atteint la pression de vapeur. Cette méthode constitue un cas de référence académique. Pour le produit, le modèle doit être explicitement sélectionné et ses hypothèses vérifiées : conduite non entièrement pressurisée, interface gaz-liquide, profil local, régime stable et capacité de transport.

| p(x*) = p_v Critère de localisation d’une transition vers une zone sans pression, selon le modèle choisi. |



| Limite du MVP Le MVP peut détecter et signaler les zones susceptibles d’être gravitaires. Une modélisation détaillée de l’écoulement à surface libre, de la séparation de colonne et de la reprise de pression doit être validée avant usage industriel. |



# 9. Réservoirs et transferts

| V = V(h) Table de barémage spécifique à chaque réservoir. |



| dV/dt = Q_in - Q_out Bilan de volume dynamique d’un bac. |



| dh/dt = (Q_in - Q_out)/(dV/dh) Évolution du niveau avec géométrie/barémage variable. |



| H_p(Q) = Δz + Δp/(ρg) + h_f(Q) + h_m(Q) Point de fonctionnement d’un transfert entre source et destination. |



| ΔM = M_entrée - M_sortie - ΔM_stock Écart de bilan matière sur une période. |



| Calcul | Entrées principales | Sorties |

| Transfert statique | Niveaux initiaux, ligne, pompe, produit | Débit initial et pressions |

| Transfert dynamique | Barémages, volume cible, pas de temps | Q(t), h_source(t), h_destination(t), durée |

| Bilan matière | Compteurs, niveaux, densités, incertitudes | Écart absolu/relatif et confiance |

| Débordement | Niveau haut/haut-haut et débit | Temps restant et arrêt requis |



# 10. Gaz réel et réseaux gaziers - phase ultérieure

| p = Z(p,T,composition) · ρRT Équation d’état du gaz réel ; Z doit provenir d’une méthode validée. |



| m_linepack = ∫ ρ(p,T,Z) A dx Inventaire de gaz contenu dans la conduite. |



Le module gaz doit traiter la compressibilité, les pressions absolues, la température, la composition, les cartes de compresseurs, le rapport de compression, le rendement et le recyclage anti-surge. Il ne doit pas réutiliser le moteur liquide en remplaçant seulement la densité.

| Élément | Modèle futur |

| Conduite gaz | Équations stationnaires compressibles puis volumes finis/DAE transitoires |

| Compresseur | Carte débit corrigé/rapport de pression/rendement/vitesse |

| Station | Lignes principales, secours, bypass, refroidisseurs et vannes |

| Stock en ligne | Bilan dynamique et prévision de livraison |

| Propriétés | Équation d’état ou bibliothèque validée pour le mélange |



# 11. Régimes transitoires - phase ultérieure

| ∂H/∂t + (a²/gA) ∂Q/∂x = 0 Équation de continuité simplifiée pour coup de bélier. |



| ∂Q/∂t + gA ∂H/∂x + RQ|Q| = 0 Équation de quantité de mouvement simplifiée. |



La méthode des caractéristiques (MOC) est la première méthode candidate pour les transitoires liquides. Les conditions aux limites doivent modéliser pompes, vannes, réservoirs, clapets et dispositifs de protection. La stabilité temporelle, la célérité, la cavitation transitoire et la séparation de colonne nécessitent des modèles et benchmarks spécifiques.

# 12. Optimisation

| min J = C_énergie + C_démarrages + C_usure + C_violations + C_mélange Fonction objectif générique, pondérations configurables. |



| sous contraintes : F(x,u)=0 ; g(x,u)≤0 ; u_discret∈{0,1} Équations physiques, limites et décisions marche/arrêt. |



| Méthode | Usage |

| Énumération filtrée | Petit nombre de pompes/configurations au MVP |

| NLP | Vitesses, pressions et débits continus |

| MILP | Planification, ressources et marche/arrêt simplifiés |

| MINLP | Décisions discrètes couplées à l’hydraulique non linéaire |

| MPC économique | Optimisation récurrente avec prévisions, phase avancée |



# 13. Diagnostics numériques et validité

| Diagnostic | Valeur enregistrée | Règle |

| Convergence | Norme du résidu, pas, itérations | Sous tolérance avant validation |

| Masse | Écart par nœud et global | Sous tolérance relative/absolue |

| Énergie | Résidu de charge | Cohérent avec pertes et machines |

| Domaine de courbe | Distance à la plage constructeur | Avertissement ou blocage |

| Propriété | Interpolation/extrapolation | Extrapolation signalée |

| Norme | Règle et édition | Version enregistrée |

| Incertitude | Entrées et propagation disponible | Affichée pour bilans sensibles |



# 14. Registre minimal des modèles

| Code | Modèle | Phase | Statut initial |

| PHY-LIQ-01 | Darcy-Weisbach et frottement | MVP | À implémenter et valider |

| PHY-LIQ-02 | Réseau stationnaire | MVP | À implémenter |

| PHY-PMP-01 | Courbes pompe et combinaisons | MVP | À implémenter |

| PHY-TNK-01 | Barémage et bilan de bac | MVP | À implémenter |

| PHY-TNK-02 | Transfert dynamique quasi-stationnaire | MVP | À implémenter |

| PHY-GRV-01 | Détection de zone gravitaire | MVP/V1 | Preuve de concept à valider |

| PHY-TRN-01 | Coup de bélier MOC | V2 | Recherche/benchmark |

| PHY-GAS-01 | Réseau gaz réel stationnaire | V4 | Moteur spécialisé |

| OPT-PMP-01 | Énumération/optimisation pompes | MVP | À implémenter |

| LDS-01 | Bilan/RTTM fuite | V5 | Données pilote requises |



# Sources et références

| Règle d’utilisation Les formules issues des documents académiques doivent être comparées aux références internationales et validées sur des cas indépendants avant intégration industrielle. |



- Documents fournis : support de modélisation des régimes de pipeline, programme Python multi-stations, cours de modélisation numérique, stockage, pompes et systèmes gaziers.

- Darcy-Weisbach, Colebrook-White, Bernoulli, bilans de masse/énergie et méthodes numériques standard.

- Normes et pratiques internationales identifiées dans D08.

- Bibliothèques scientifiques étudiées dans D14.

Fin du document