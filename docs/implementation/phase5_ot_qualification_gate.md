# P5-I — Gate de qualification OT-0 à OT-5

Références : D15 §14 et contrat Phase 5.

Cette brique matérialise la séquence de preuves prévue par le cahier des charges :

- OT-0 : atelier avec l’opérateur — architecture, protocoles, politiques ;
- OT-1 : POC hors ligne sur simulateur OPC UA ;
- OT-2 : passerelle en laboratoire et tests de sécurité ;
- OT-3 : connexion à une réplique ou un historian de test ;
- OT-4 : pilote en lecture seule en DMZ ;
- OT-5 : qualification disponibilité et données.

`assess_ot_qualification` n’exécute aucun test OT et ne déduit aucun résultat. Pour chaque étape demandée, il exige une preuve, un protocole, un environnement et un résultat observé. Une étape absente ou déclarée en échec reste bloquante et sa preuve reste visible dans le résultat.

Le passage du gate signifie uniquement que les preuves déclarées OT-0…OT-n sont présentes et marquées réussies selon leurs protocoles référencés. Il ne constitue ni une certification IEC 62443/62541, ni une autorisation de connexion à un site réel, ni une validation de sûreté.
