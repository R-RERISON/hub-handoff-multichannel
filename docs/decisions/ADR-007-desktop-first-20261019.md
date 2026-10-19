# ADR-007 — Escopo desktop-first para Handoff Hub (19/10/2026)

**Status**: APPROVED_FOR_SCOPE (decisão expressa de produto na conversa) — não é gate de código,
aprovação de release, nem aprovação de segurança.

## Contexto

O Product Owner determinou: **o sistema será utilizado majoritariamente em
desktops; não haverá suporte mobile planejado nesta fase**, e solicitou
continuidade do desenvolvimento das SPECs, sem aguardar a correção de
capturas mobile `390×844`.

A rodada SPEC-006C no SHA `75ad2e4f739a5a4e463ff1efcb1b72b2537ff93e`
teve gates automatizados PASS e 11 PNGs apresentados para inspeção.
Os dois PNGs de 390×844 foram considerados evidência inválida por
renderização/captura com iframe escalonado (~293×635 no conteúdo).
Isso **não é PASS mobile nem bug CSS confirmado**.

## Decisão

1. **Viewports formalmente suportados nesta fase**: `1366×768` e
   `1920×1080`, Chrome ou Edge desktop, escala padrão de viewport
   verificada. Em menor janela, comportamento best-effort, **sem aceite
   mobile**. Não tratar PWA nem aplicativo para celular como requisitos.
2. A condição obrigatória de `390×844` em SPEC-006C/007/018 passa a
   **OUT_OF_SCOPE_BY_PRODUCT_DECISION**, não `PASS`, `WAIVED_SECURITY`
   ou `FAILED_CSS`. Preservar histórico do teste e a ressalva dos PNGs.
3. Permanecem obrigatórios: fluxo funcional UX-02 e UX-05, leitura por
   segmento, privacidade/autorizações N1/N2, teclado, foco visível e
   verificação de legibilidade/zoom nos desktops.
4. A mudança de escopo **não dispensa** revisão do diff, segurança, rollback,
   migração somente TEMP e autorização humana para promover o PR #28.
   Todas as branches continuam Draft, sem merge automático.
5. A SPEC-018 passa a documentar contratos desktop-first, mantendo critérios
   WCAG aplicáveis à web desktop. Mobile pode ser reavaliado em SPEC futura.

## Consequências

- O histórico do `release_ui_evidence_gate` tem 11 slots; não reescrever
  silenciosamente o gate antigo para chamar mobile PASS.
- SPEC-007 pode avançar em branch de feature isolada mesmo com revisão final
  do PR #28 pendente: **desenvolver não significa integrar à main**.
- QA de qualquer mudança deve registrar versão do código, laboratório,
  dispositivo/browser real e decisão por critério; revalidar ao mudar o SHA.
- Rollback desta decisão: nova autorização expressa de escopo e nova matriz
  de aceite; não reescrever evidência anterior.

## Riscos residuais

Telas em larguras inferiores a 1366 podem apresentar cortes/scroll; o
produto não anuncia suporte a esses dispositivos. Zoom e acessibilidade
devem ser analisados como requisitos independentes, não confundidos com
viewport mobile.
