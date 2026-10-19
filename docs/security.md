# Requisitos de segurança e privacidade — baseline

1. Entra ID e OIDC para humanos; RBAC para operadores, supervisores e admins por operação.
2. OAuth 2.0 client credentials, scopes e audience para bots e integrações.
3. Webhooks autenticados, retry, proteção contra replay e assinaturas quando aplicáveis.
4. SQL parametrizado; autorização obrigatória no recurso antes de consultar dados (prevenir BOLA/IDOR).
5. Times UTC, correlação, auditoria com minimização de PII; retenção configurada conforme política institucional/LGPD.
6. Anexos sujeitos a verificação de tipo, tamanho, malware, autorização de download e mitigação de SSRF.
7. Segredos em vault ou infraestrutura equivalente; proibir logs de tokens e conteúdos integrais.
8. Multioperação e multitenancy isoladas inclusive em cache, filas, websocket e relatórios.
9. Threat modeling antes de SPEC-002 e revisão independente antes do piloto Teams.
10. Repositório privado não autoriza armazenamento de ativos internos ou dados reais.
