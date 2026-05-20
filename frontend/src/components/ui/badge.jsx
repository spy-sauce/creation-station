/**
 * Badge — Status/label badge component.
 * Per NUTRIENTS.md §B — Component Prop Contracts (frozen).
 *
 * Props interface:
 * - children: ReactNode (required)
 * - variant: 'default' | 'primary' | 'success' | 'warning' | 'destructive'
 * - size: 'sm' | 'md'
 * - className: string
 */

import { forwardRef } from 'react'

/**
 * Variant style mappings using CSS custom properties.
 * Per NUTRIENTS.md §F — no hex literals in JSX.
 */
const variantStyles = {
  default: {
    background: 'var(--bg-tertiary)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
  },
  primary: {
    background: 'var(--gold-faint)',
    color: 'var(--gold)',
    border: '1px solid var(--gold-dim)',
  },
  success: {
    background: 'rgba(34, 197, 94, 0.1)',
    color: 'var(--status-success)',
    border: '1px solid rgba(34, 197, 94, 0.3)',
  },
  warning: {
    background: 'rgba(234, 179, 8, 0.1)',
    color: 'var(--status-warning)',
    border: '1px solid rgba(234, 179, 8, 0.3)',
  },
  destructive: {
    background: 'rgba(239, 68, 68, 0.1)',
    color: 'var(--status-error)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
  },
}

/**
 * Size mappings.
 */
const sizeStyles = {
  sm: {
    padding: '2px 6px',
    fontSize: '9px',
  },
  md: {
    padding: '4px 10px',
    fontSize: '10px',
  },
}

const Badge = forwardRef(function Badge(
  {
    children,
    variant = 'default',
    size = 'md',
    className,
    style,
    ...rest
  },
  ref
) {
  const variantStyle = variantStyles[variant] || variantStyles.default
  const sizeStyle = sizeStyles[size] || sizeStyles.md

  const badgeStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: variantStyle.background,
    color: variantStyle.color,
    border: variantStyle.border,
    padding: sizeStyle.padding,
    fontFamily: 'var(--font-mono)',
    fontSize: sizeStyle.fontSize,
    fontWeight: 'var(--font-medium)',
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    whiteSpace: 'nowrap',
    ...style,
  }

  return (
    <span ref={ref} style={badgeStyle} className={className} {...rest}>
      {children}
    </span>
  )
})

export default Badge
