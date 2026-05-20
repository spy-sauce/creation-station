/**
 * Input — Text input component.
 * Per NUTRIENTS.md §B — Component Prop Contracts (frozen).
 *
 * Props interface:
 * - label: string
 * - helperText: string
 * - error: string
 * - leftIcon: LucideIcon
 * - rightIcon: LucideIcon
 * - ...rest: InputHTMLAttributes
 */

import { forwardRef, useId } from 'react'

const Input = forwardRef(function Input(
  {
    label,
    helperText,
    error,
    leftIcon: LeftIcon,
    rightIcon: RightIcon,
    style,
    className,
    ...rest
  },
  ref
) {
  const id = useId()
  const inputId = rest.id || id

  const hasLeftIcon = Boolean(LeftIcon)
  const hasRightIcon = Boolean(RightIcon)

  const wrapperStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-2)',
  }

  const labelStyle = {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '0.2em',
    textTransform: 'uppercase',
    color: 'var(--text-secondary)',
  }

  const inputWrapperStyle = {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  }

  const iconStyle = {
    position: 'absolute',
    width: 14,
    height: 14,
    color: 'var(--text-muted)',
    strokeWidth: 1.5,
    pointerEvents: 'none',
  }

  const leftIconStyle = {
    ...iconStyle,
    left: 14,
  }

  const rightIconStyle = {
    ...iconStyle,
    right: 14,
  }

  const inputStyle = {
    width: '100%',
    background: 'var(--bg-tertiary)',
    border: `1px solid ${error ? 'var(--status-error)' : 'var(--border)'}`,
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-sans)',
    fontSize: '14px',
    fontWeight: 300,
    padding: '14px 18px',
    paddingLeft: hasLeftIcon ? '42px' : '18px',
    paddingRight: hasRightIcon ? '42px' : '18px',
    outline: 'none',
    transition: 'border-color var(--duration-normal) var(--ease-default)',
    appearance: 'none',
    ...style,
  }

  const helperStyle = {
    fontFamily: 'var(--font-sans)',
    fontSize: '12px',
    color: error ? 'var(--status-error)' : 'var(--text-muted)',
  }

  return (
    <div style={wrapperStyle} className={className}>
      {label && (
        <label htmlFor={inputId} style={labelStyle}>
          {label}
        </label>
      )}
      <div style={inputWrapperStyle}>
        {LeftIcon && <LeftIcon style={leftIconStyle} />}
        <input
          ref={ref}
          id={inputId}
          style={inputStyle}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = error ? 'var(--status-error)' : 'var(--gold)'
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = error ? 'var(--status-error)' : 'var(--border)'
          }}
          {...rest}
        />
        {RightIcon && <RightIcon style={rightIconStyle} />}
      </div>
      {(helperText || error) && (
        <span style={helperStyle}>{error || helperText}</span>
      )}
    </div>
  )
})

export default Input
