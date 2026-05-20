/**
 * Card — Container component with variants.
 * Per NUTRIENTS.md §B — Component Prop Contracts (frozen).
 *
 * Props interface:
 * - children: ReactNode (required)
 * - variant: 'default' | 'elevated' | 'outlined' | 'flat'
 * - padding: 'none' | 'sm' | 'md' | 'lg'
 * - ...rest: HTMLAttributes<HTMLDivElement>
 */

import { forwardRef } from 'react'

/**
 * Variant style mappings using CSS custom properties.
 * Per NUTRIENTS.md §F — no hex literals in JSX.
 */
const variantStyles = {
  default: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border)',
    boxShadow: 'none',
  },
  elevated: {
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    boxShadow: 'var(--shadow-md)',
  },
  outlined: {
    background: 'transparent',
    border: '1px solid var(--border)',
    boxShadow: 'none',
  },
  flat: {
    background: 'var(--bg-tertiary)',
    border: 'none',
    boxShadow: 'none',
  },
}

/**
 * Padding mappings.
 */
const paddingStyles = {
  none: '0',
  sm: 'var(--space-3)',
  md: 'var(--space-5)',
  lg: 'var(--space-8)',
}

const Card = forwardRef(function Card(
  {
    children,
    variant = 'default',
    padding = 'md',
    style,
    className,
    ...rest
  },
  ref
) {
  const variantStyle = variantStyles[variant] || variantStyles.default
  const paddingValue = paddingStyles[padding] || paddingStyles.md

  const cardStyle = {
    background: variantStyle.background,
    border: variantStyle.border,
    boxShadow: variantStyle.boxShadow,
    padding: paddingValue,
    transition: 'border-color var(--duration-normal) var(--ease-default), box-shadow var(--duration-normal) var(--ease-default)',
    ...style,
  }

  return (
    <div ref={ref} style={cardStyle} className={className} {...rest}>
      {children}
    </div>
  )
})

/**
 * CardHeader — Standard card header section.
 */
export function CardHeader({ children, style, ...rest }) {
  return (
    <div
      style={{
        padding: 'var(--space-4) var(--space-5)',
        borderBottom: '1px solid var(--border)',
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  )
}

/**
 * CardContent — Standard card body section.
 */
export function CardContent({ children, style, ...rest }) {
  return (
    <div style={{ padding: 'var(--space-5)', ...style }} {...rest}>
      {children}
    </div>
  )
}

/**
 * CardFooter — Standard card footer section.
 */
export function CardFooter({ children, style, ...rest }) {
  return (
    <div
      style={{
        padding: 'var(--space-4) var(--space-5)',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        gap: 'var(--space-3)',
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  )
}

export default Card
