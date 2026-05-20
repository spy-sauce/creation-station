/**
 * Spinner — Loading indicator component.
 * Per NUTRIENTS.md §B — Component Prop Contracts (frozen).
 *
 * Props interface:
 * - size: 'sm' | 'md' | 'lg'
 * - className: string
 */

import { forwardRef } from 'react'

/**
 * Size mappings.
 */
const sizeStyles = {
  sm: { width: 16, height: 16, borderWidth: 2 },
  md: { width: 24, height: 24, borderWidth: 2 },
  lg: { width: 36, height: 36, borderWidth: 2 },
}

const Spinner = forwardRef(function Spinner(
  { size = 'md', className, style, ...rest },
  ref
) {
  const sizeStyle = sizeStyles[size] || sizeStyles.md

  const spinnerStyle = {
    width: sizeStyle.width,
    height: sizeStyle.height,
    border: `${sizeStyle.borderWidth}px solid var(--border)`,
    borderTopColor: 'var(--gold)',
    borderRadius: 'var(--radius-full)',
    animation: 'spin 1s linear infinite',
    ...style,
  }

  return <div ref={ref} style={spinnerStyle} className={className} {...rest} />
})

export default Spinner
