/**
 * Button — Primary action component.
 * Per NUTRIENTS.md §B — Component Prop Contracts (frozen).
 *
 * Props interface:
 * - children: ReactNode (required)
 * - variant: 'default' | 'primary' | 'secondary' | 'ghost' | 'destructive' | 'outline'
 * - size: 'sm' | 'md' | 'lg'
 * - loading: boolean
 * - fullWidth: boolean
 * - leftIcon: LucideIcon
 * - rightIcon: LucideIcon
 * - asChild: boolean (not implemented — would require Radix Slot)
 * - ...rest: ButtonHTMLAttributes
 */

import { forwardRef } from 'react'

/**
 * Variant style mappings using CSS custom properties.
 * Per NUTRIENTS.md §F — no hex literals in JSX.
 */
const variantStyles = {
  default: {
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
    hoverBg: 'var(--bg-elevated)',
  },
  primary: {
    background: 'var(--gold)',
    color: 'var(--bg-primary)',
    border: 'none',
    hoverBg: 'var(--accent-hover)',
  },
  secondary: {
    background: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
    hoverBg: 'var(--bg-tertiary)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    hoverBg: 'var(--bg-tertiary)',
  },
  destructive: {
    background: 'var(--destructive)',
    color: 'var(--text-primary)',
    border: 'none',
    hoverBg: 'var(--destructive-hover)',
  },
  outline: {
    background: 'transparent',
    color: 'var(--gold)',
    border: '1px solid var(--gold)',
    hoverBg: 'var(--gold-faint)',
  },
}

/**
 * Size style mappings.
 */
const sizeStyles = {
  sm: {
    padding: '8px 16px',
    fontSize: '10px',
    iconSize: 12,
  },
  md: {
    padding: '12px 24px',
    fontSize: '11px',
    iconSize: 14,
  },
  lg: {
    padding: '16px 36px',
    fontSize: '12px',
    iconSize: 16,
  },
}

const Button = forwardRef(function Button(
  {
    children,
    variant = 'default',
    size = 'md',
    loading = false,
    fullWidth = false,
    leftIcon: LeftIcon,
    rightIcon: RightIcon,
    disabled,
    style,
    className,
    ...rest
  },
  ref
) {
  const variantStyle = variantStyles[variant] || variantStyles.default
  const sizeStyle = sizeStyles[size] || sizeStyles.md

  const baseStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    background: variantStyle.background,
    color: variantStyle.color,
    border: variantStyle.border,
    padding: sizeStyle.padding,
    fontFamily: 'var(--font-mono)',
    fontSize: sizeStyle.fontSize,
    fontWeight: 'var(--font-medium)',
    letterSpacing: '0.15em',
    textTransform: 'uppercase',
    textDecoration: 'none',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled || loading ? 0.5 : 1,
    width: fullWidth ? '100%' : 'auto',
    transition: 'background var(--duration-normal) var(--ease-default), border-color var(--duration-normal) var(--ease-default), color var(--duration-normal) var(--ease-default)',
    ...style,
  }

  const iconStyle = {
    width: sizeStyle.iconSize,
    height: sizeStyle.iconSize,
    strokeWidth: 1.5,
  }

  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={className}
      style={baseStyle}
      onMouseEnter={(e) => {
        if (!disabled && !loading) {
          e.currentTarget.style.background = variantStyle.hoverBg
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = variantStyle.background
      }}
      {...rest}
    >
      {loading ? (
        <span
          style={{
            width: sizeStyle.iconSize,
            height: sizeStyle.iconSize,
            border: '2px solid currentColor',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }}
        />
      ) : (
        LeftIcon && <LeftIcon style={iconStyle} />
      )}
      {children}
      {!loading && RightIcon && <RightIcon style={iconStyle} />}
    </button>
  )
})

export default Button
