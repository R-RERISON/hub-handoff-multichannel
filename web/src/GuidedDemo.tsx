import { ArrowRight, Check, CheckCheck, CircleHelp, MessageCircle, UserRoundCheck } from 'lucide-react'

export type JourneyStage = 'create' | 'assign' | 'pending' | 'receive' | 'reply' | 'close' | 'done'

type GuidedDemoProps = {
  stage: JourneyStage
  busy: boolean
  hasWaiting: boolean
  availableOperators: number
  onCreate: () => void
  onAssign: () => void
  onSimulateUser: () => void
  onFocusReply: () => void
  onClose: () => void
  onGoOperator: () => void
}

const steps = [
  { label: 'Abrir', detail: 'Criar uma solicitação' },
  { label: 'Distribuir', detail: 'Atribuir a operador' },
  { label: 'Conversar', detail: 'Trocar mensagens' },
  { label: 'Concluir', detail: 'Encerrar atendimento' },
]

const stepIndex: Record<JourneyStage, number> = {
  create: 0,
  assign: 1,
  pending: 1,
  receive: 2,
  reply: 2,
  close: 3,
  done: 4,
}

export default function GuidedDemo({
  stage,
  busy,
  hasWaiting,
  availableOperators,
  onCreate,
  onAssign,
  onSimulateUser,
  onFocusReply,
  onClose,
  onGoOperator,
}: GuidedDemoProps) {
  const progress = stepIndex[stage]
  const guidance = {
    create: {
      title: 'Comece por uma solicitação',
      description: 'Crie uma conversa fictícia. Ela entrará na fila Suporte N1.',
      button: 'Criar solicitação de teste',
      action: onCreate,
      blocked: false,
    },
    assign: {
      title: 'Agora, atribua um operador',
      description: 'O próximo atendimento da fila será direcionado a um operador livre.',
      button: 'Distribuir próximo da fila',
      action: onAssign,
      blocked: !hasWaiting || availableOperators === 0,
    },
    pending: {
      title: 'Aguardando o aceite do operador',
      description: 'Uma oferta foi enviada. Abra a Mesa do Operador para aceitar ou recusar.',
      button: 'Abrir Mesa do Operador',
      action: onGoOperator,
      blocked: false,
    },
    receive: {
      title: 'Simule uma mensagem do usuário',
      description: 'O atendimento está ativo. Gere uma mensagem recebida para iniciar a conversa.',
      button: 'Receber mensagem de teste',
      action: onSimulateUser,
      blocked: false,
    },
    reply: {
      title: 'Responda como operador',
      description: 'Prepare sua resposta no campo de mensagem e envie. Ela ficará na outbox local.',
      button: 'Preparar resposta do operador',
      action: onFocusReply,
      blocked: false,
    },
    close: {
      title: 'Conclua o atendimento',
      description: 'A resposta foi registrada. Encerre a sessão para liberar a capacidade do operador.',
      button: 'Encerrar atendimento',
      action: onClose,
      blocked: false,
    },
    done: {
      title: 'Fluxo demonstrado com sucesso',
      description: 'Atendimento encerrado. Você pode repetir a simulação criando uma nova solicitação.',
      button: 'Criar outro atendimento',
      action: onCreate,
      blocked: false,
    },
  }[stage]

  return (
    <section className="journey" aria-label="Roteiro guiado de homologação">
      <div className="journey__header">
        <div className="journey__tag"><CircleHelp size={14} /> TESTE GUIADO</div>
        <div className="journey__description" aria-live="polite">
          <strong>{guidance.title}</strong>
          <span>{guidance.description}</span>
          {stage === 'assign' && availableOperators === 0 && (
            <span className="journey__warning">Nenhum operador livre. Altere a presença em Operadores.</span>
          )}
        </div>
        <button
          type="button"
          className="primary journey__action"
          disabled={busy || guidance.blocked}
          onClick={guidance.action}
        >
          {stage === 'done' ? <CheckCheck size={16} /> : <ArrowRight size={16} />}
          {guidance.button}
        </button>
      </div>
      <ol className="journey__steps" aria-label="Etapas do atendimento">
        {steps.map((step, index) => (
          <li
            key={step.label}
            className={[
              'journey__step',
              index < progress ? 'journey__step--done' : '',
              index === progress ? 'journey__step--current' : '',
            ].join(' ')}
            aria-current={index === progress ? 'step' : undefined}
          >
            <span className="journey__number">{index < progress ? <Check size={13} /> : index + 1}</span>
            <span>{step.label}</span>
          </li>
        ))}
      </ol>
      <div className="journey__explanation">
        <MessageCircle size={14} />
        <span>Simulação local · O usuário conversa pelo bot de origem apenas após a integração Teams</span>
        <UserRoundCheck size={14} />
      </div>
    </section>
  )
}
