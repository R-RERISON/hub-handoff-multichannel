import type { ReactNode } from 'react'

type EmptyStateProps = {
  children: ReactNode
  className?: string
}

/** Informational empty state only; authorization remains exclusively in the API. */
export function EmptyState({ children, className = '' }: EmptyStateProps) {
  return <div className={['hub-empty-state', className].filter(Boolean).join(' ')}
    role="status">{children}</div>
}
