# Mapa de compatibilidade do legado (sem código proprietário)

| Comportamento observado | Novo componente | Observações |
|---|---|---|
| handoff GET/POST no Tornado | integrations/legacy_tornado | Adapter com feature flag |
| listaAtendimento / listaPermissaoHandoff | Sessions/Auth persistentes | Remover estado em memória como fonte de verdade |
| status do operador | Operators/Presence | Estado e transição auditáveis |
| posição e distribuição em fila | Queues/Dispatch | SQL transacional e lock sob concorrência |
| Cisco Finesse | integrations/finesse | Provider opcional |
| envio de mensagens Teams | Adapter Teams no bot original | Não reutilizar a identidade entre bots |
| anexos/imagens | Messaging/Attachments | Antivírus, ACL, limites e retentativas |
| ociosidade/transferência | SLA/Workers | Tarefas duráveis, reinício seguro |
| pesquisa de satisfação | CSAT | Evento após encerramento |
| identificadores de sessão | Session correlation | Migração e reconciliação em homologação |

Riscos identificados por leitura estática do código fornecido: SQL interpolado, estado global, requisições bloqueantes em rotinas assíncronas, alocação sem reserva atômica explícita, tarefas não duráveis. Isto não equivale a evidência de incidente em produção.

Não copiar código, credenciais, dados corporativos, nomes, URLs ou payloads reais ao repositório.
