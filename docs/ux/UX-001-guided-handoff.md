# UX-001 — Jornada intuitiva da POC de atendimento

Data: 2026-10-15 | Implementação: branch `feat/002-sqlite-poc`
Status: desenvolvimento publicado; homologação visual e build no Windows pendentes.

## Evidência e problema

A primeira POC foi validada com sucesso no VS Code: backend com 21 testes aprovados, build React/Vite concluído e fluxo manual de atendimento funcionando. O usuário relatou que a experiência **não foi intuitiva**.

Causas observáveis na interface anterior:
- Botão **Simular** não esclarecia se gerava conversa, mensagem ou atendimento.
- A ação de distribuição estava em um card lateral separado da conversa.
- Após criar uma solicitação, não havia um indicador claro da próxima ação.
- As mensagens de teste do usuário e as respostas do operador ficavam misturadas na barra inferior.
- Estados vazios ocupavam grande área sem instrução ou CTA adequado.
- O cockpit podia exigir rolagem vertical mesmo sem conteúdo suficiente.

## Objetivo UX

O operador/homologador deve saber **o que fazer agora** sem instruções externas. Manter o usuário no centro da jornada, ainda que os dados sejam fictícios.

## Solução implementada

1. **Teste guiado** com progresso em quatro etapas: Abrir, Distribuir, Conversar, Concluir.
2. CTA contextual em cada etapa:
   - Criar solicitação de teste.
   - Distribuir próximo da fila.
   - Receber mensagem de teste.
   - Preparar resposta do operador.
   - Encerrar atendimento.
3. Ao distribuir, **selecionar a sessão realmente atribuída** pela fila (a mais antiga), evitando mostrar outro atendimento como se tivesse sido alocado.
4. Mensagens de retorno com `role=status`, sem falso feedback de sucesso quando a API falha.
5. Estados vazios instrutivos e ações explícitas no painel central.
6. Resposta do operador com texto sugerido editável; envio apenas mediante clique do operador.
7. Layout desktop com rolagem local nas colunas de conversas/mensagens.
8. Identificar permanentemente que a mensagem é simulada e que não há envio ao Teams.

## Cenário de homologação UX-001

| Etapa | Ação visual | Resultado esperado |
|---|---|---|
| 1 | Abrir Conversas; clicar **Criar solicitação de teste** | Sessão criada, foco na conversa e próximo passo exibido |
| 2 | Clicar **Distribuir próximo da fila** | Sessão mais antiga recebe operador; indicador de fila atualiza |
| 3 | Clicar **Receber mensagem de teste** | Mensagem de usuário surge no histórico |
| 4 | Clicar **Preparar resposta do operador** | Campo de resposta recebe sugestão editável e ganha foco |
| 5 | Clicar **Enviar resposta** | Mensagem aparece no histórico; outbox incrementa |
| 6 | Clicar **Encerrar atendimento** | Estado encerrado; capacidade de operador liberada |
| 7 | Clicar **Criar outro atendimento** | Inicia nova jornada sem reiniciar aplicação |

### Cenários alternativos

- Fila vazia: botão de distribuir desabilitado; UI oferece criação.
- Operadores indisponíveis: ação bloqueada com orientação para alterar presença em **Operadores**.
- Vários tickets pendentes: a próxima distribuição abre a conversa que foi realmente atribuída, podendo ser outra que não a originalmente selecionada.
- Falha no envio: manter texto digitado e mostrar erro; nunca declarar entrega ao Teams.
- Atualização do navegador: dados da sessão persistem em SQLite; chave permanece apenas na memória da página.

## Gates locais

Executar `./start.cmd --check` no Windows PowerShell (na raiz do repositório), depois `./start.cmd`. Validar o fluxo e enviar print em caso de divergência. **Não utilizar GitHub Actions.**

## Próxima evolução

Esta versão orienta a **homologação simulada**, não substitui as futuras interfaces operacionais de operador/supervisor nem as regras reais de oferta/aceite, SLA e integração Teams.
