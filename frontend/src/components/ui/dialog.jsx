/**
 * Dialog — Modal dialog component.
 * Per NUTRIENTS.md §B — Component Prop Contracts (frozen).
 *
 * Props interface:
 * - open: boolean (required)
 * - onOpenChange: (open: boolean) => void (required)
 * - children: ReactNode (required)
 */

import { useEffect, useCallback } from 'react'
import { X } from 'lucide-react'

/**
 * Dialog root component.
 */
export default function Dialog({ open, onOpenChange, children }) {
  // Close on escape key
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') {
        onOpenChange(false)
      }
    },
    [onOpenChange]
  )

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [open, handleKeyDown])

  if (!open) return null

  const overlayStyle = {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.8)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 'var(--space-6)',
    zIndex: 100,
    animation: 'fadeIn 0.2s ease-out',
  }

  return (
    <div style={overlayStyle} onClick={() => onOpenChange(false)}>
      {children}
    </div>
  )
}

/**
 * DialogContent — The modal content container.
 */
export function DialogContent({ children, style, ...rest }) {
  const contentStyle = {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border)',
    maxWidth: 480,
    width: '100%',
    maxHeight: '85vh',
    overflow: 'auto',
    position: 'relative',
    animation: 'fadeIn 0.2s ease-out',
    ...style,
  }

  return (
    <div style={contentStyle} onClick={(e) => e.stopPropagation()} {...rest}>
      {children}
    </div>
  )
}

/**
 * DialogHeader — Header section with title and close button.
 */
export function DialogHeader({ children, onClose, style, ...rest }) {
  const headerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 'var(--space-5)',
    borderBottom: '1px solid var(--border)',
    ...style,
  }

  const closeButtonStyle = {
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    padding: 'var(--space-1)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'color var(--duration-fast) var(--ease-default)',
  }

  return (
    <div style={headerStyle} {...rest}>
      <div style={{ flex: 1 }}>{children}</div>
      {onClose && (
        <button
          style={closeButtonStyle}
          onClick={onClose}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          aria-label="Close"
        >
          <X style={{ width: 18, height: 18, strokeWidth: 1.5 }} />
        </button>
      )}
    </div>
  )
}

/**
 * DialogTitle — Title text for the dialog.
 */
export function DialogTitle({ children, style, ...rest }) {
  const titleStyle = {
    fontFamily: 'var(--font-serif)',
    fontSize: 'var(--text-xl)',
    fontWeight: 'var(--font-normal)',
    color: 'var(--text-primary)',
    lineHeight: 'var(--leading-tight)',
    ...style,
  }

  return (
    <h2 style={titleStyle} {...rest}>
      {children}
    </h2>
  )
}

/**
 * DialogDescription — Description text below title.
 */
export function DialogDescription({ children, style, ...rest }) {
  const descStyle = {
    fontFamily: 'var(--font-sans)',
    fontSize: 'var(--text-sm)',
    color: 'var(--text-secondary)',
    marginTop: 'var(--space-2)',
    ...style,
  }

  return (
    <p style={descStyle} {...rest}>
      {children}
    </p>
  )
}

/**
 * DialogBody — Main content area.
 */
export function DialogBody({ children, style, ...rest }) {
  const bodyStyle = {
    padding: 'var(--space-5)',
    ...style,
  }

  return (
    <div style={bodyStyle} {...rest}>
      {children}
    </div>
  )
}

/**
 * DialogFooter — Footer with actions.
 */
export function DialogFooter({ children, style, ...rest }) {
  const footerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 'var(--space-3)',
    padding: 'var(--space-5)',
    borderTop: '1px solid var(--border)',
    ...style,
  }

  return (
    <div style={footerStyle} {...rest}>
      {children}
    </div>
  )
}
