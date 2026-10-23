import { useEffect, useId, useRef } from 'react'

type Props = {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  busy?: boolean
  danger?: boolean
  onCancel: () => void
  onConfirm: () => void
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  busy = false,
  danger = false,
  onCancel,
  onConfirm,
}: Props) {
  const dialogRef = useRef<HTMLDialogElement|null>(null)
  const cancelRef = useRef<HTMLButtonElement|null>(null)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    else if (!open && dialog.open) dialog.close()
  }, [open])

  useEffect(() => {
    if (open) cancelRef.current?.focus()
  }, [open])

  return <dialog ref={dialogRef} className="confirm-dialog" role="alertdialog"
    aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId}
    onCancel={event => { event.preventDefault(); if (!busy) onCancel() }}
    onKeyDown={event => {
      if (event.key !== 'Tab') return
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLButtonElement>(
        'button:not(:disabled)',
      ) ?? [])
      if (focusable.length < 2) return
      const currentIndex = focusable.findIndex(button => button === document.activeElement)
      const nextIndex = (currentIndex + (event.shiftKey ? -1 : 1) + focusable.length) % focusable.length
      event.preventDefault()
      focusable[nextIndex].focus()
    }}>
    <h2 id={titleId}>{title}</h2>
    <p id={descriptionId}>{description}</p>
    <div className="confirm-dialog__actions">
      <button ref={cancelRef} type="button" className="outline" disabled={busy}
        onClick={onCancel}>Cancelar</button>
      <button type="button" className={danger?'confirm-dialog__danger':'primary'}
        disabled={busy} onClick={onConfirm}>
        {busy?'Salvando…':confirmLabel}
      </button>
    </div>
  </dialog>
}
