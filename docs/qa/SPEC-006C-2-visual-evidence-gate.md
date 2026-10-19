# SPEC-006C — Gate de integridade das capturas UX (não substitui revisão humana)

O utilitário scripts/release_ui_evidence_gate.py confirma apenas se 11 screenshots
PNG distintos, capturados em resoluções reais, correspondem aos cenários
e ao SHA atual de código. Não interpreta visual, login, isolamento, redaction
nem concede aprovação: result=EVIDENCE_READY_FOR_MANUAL_REVIEW não é PASS.

## Usar no Windows e somente no lab TEMP validado

1. Na branch da feature, execute: start.cmd --lab --lab-dir <TEMP>.
2. Inicialize o manifesto sem sobrescrever evidências existentes:

~~~powershell
.\.venv\Scripts\python.exe -m scripts.release_ui_evidence_gate --lab "<TEMP>" --init
~~~

3. O arquivo <TEMP>/qa-evidence/manifest.json registra o SHA de git HEAD,
cenários e nomes exatos esperados. Em navegador externo Chrome/Edge,
reproduza e salve cada PNG com o viewport indicado no próprio arquivo:
- UX-08: histórico Auditor e Mesa Operador a 390×844, 1366×768, 1920×1080;
- UX-02: histórico Supervisor N1 e N2 a 1366×768;
- UX-05: histórico Supervisor N1 e N2 e Mesa Operador N2 a 1366×768.

4. Execute:

~~~powershell
.\.venv\Scripts\python.exe -m scripts.release_ui_evidence_gate --lab "<TEMP>" --check
~~~

O verificador recusa manifestos com SHA divergente, imagens incompletas,
capturas reutilizadas, dimensões erradas, paths externos, symlink e qualquer
banco que não seja TEMP 006b4. Não expõe imagens nem credenciais na saída.

Após ter todas as imagens, revisores QA/segurança devem atestar manualmente
perfil autenticado, dados exclusivamente sintéticos, visibilidade N1/N2,
ausência de nota interna no histórico, controles por teclado, responsividade
sem cortes, overflow e ocultação de dados após revogação. Só então
registrar PASS ou FAIL no PR #28 e issue #29, nunca por saída automática.

Nenhuma captura foi produzida por esta implementação.
