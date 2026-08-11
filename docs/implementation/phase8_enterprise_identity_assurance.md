# P8-F — Assurance d’identité OIDC / MFA

Références : D15 sécurité et historisation, D17 industrialisation, contrat Phase 8.

PETROLE dispose déjà d’une authentification locale JWT + refresh token et d’un contrôle de rôles. Pour le pilote/produit industriel, le cahier des charges demande MFA pour les administrateurs et privilégie un annuaire/OIDC lorsque l’opérateur l’exige.

Cette étape n’impose aucun fournisseur OIDC et aucune technologie MFA non sélectionnée. `enterprise_identity.py` définit seulement le contrat que devra respecter l’adaptateur d’identité retenu : issuer HTTPS, audience PETROLE, subject stable, méthodes d’authentification `amr`, instant d’authentification et identifiant du jeton.

`MfaAssurancePolicy` rend explicites les rôles soumis à MFA et les valeurs `amr` acceptées par la politique du site. `assess_verified_oidc_claims` refuse un issuer/audience inattendu ou l’absence d’une méthode MFA autorisée pour un rôle concerné. Aucun fallback implicite vers le mot de passe seul n’est effectué.

Le module reçoit volontairement des `VerifiedOidcClaims` : la vérification cryptographique de la signature, du JWKS, de l’expiration, du nonce/PKCE et des autres contraintes de protocole restera dans l’adaptateur OIDC concret lorsque le fournisseur sera sélectionné. Une réussite de ce contrôle d’assurance n’est donc pas, à elle seule, une authentification réseau complète ni une certification de sécurité.
