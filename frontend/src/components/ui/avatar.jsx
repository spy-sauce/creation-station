/**
 * Avatar — User avatar with fallback.
 * Per NUTRIENTS.md §B — Component Prop Contracts (frozen).
 *
 * Props interface:
 * - src: string (image URL)
 * - alt: string
 * - fallback: string (initials)
 * - size: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
 * - shape: 'circle' | 'square'
 * - className: string
 */

import { forwardRef, useState } from 'react'

/**
 * Size mappings.
 */
const sizeStyles = {
  xs: { width: 24, height: 24, fontSize: 8 },
  sm: { width: 32, height: 32, fontSize: 10 },
  md: { width: 40, height: 40, fontSize: 12 },
  lg: { width: 48, height: 48, fontSize: 14 },
  xl: { width: 64, height: 64, fontSize: 18 },
}

/**
 * Shape mappings.
 */
const shapeStyles = {
  circle: 'var(--radius-full)',
  square: 'var(--radius-md)',
}

const Avatar = forwardRef(function Avatar(
  {
    src,
    alt = '',
    fallback,
    size = 'md',
    shape = 'circle',
    className,
    style,
    ...rest
  },
  ref
) {
  const [imageError, setImageError] = useState(false)
  const sizeStyle = sizeStyles[size] || sizeStyles.md
  const borderRadius = shapeStyles[shape] || shapeStyles.circle

  const showFallback = !src || imageError

  const containerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: sizeStyle.width,
    height: sizeStyle.height,
    borderRadius,
    border: '1px solid var(--border)',
    background: showFallback ? 'var(--bg-tertiary)' : 'transparent',
    overflow: 'hidden',
    flexShrink: 0,
    ...style,
  }

  const imageStyle = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  }

  const fallbackStyle = {
    fontFamily: 'var(--font-mono)',
    fontSize: sizeStyle.fontSize,
    fontWeight: 'var(--font-medium)',
    color: 'var(--gold)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  }

  // Generate fallback initials from alt text if no explicit fallback
  const initials = fallback || (alt ? alt.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : '?')

  return (
    <div ref={ref} style={containerStyle} className={className} {...rest}>
      {!showFallback ? (
        <img
          src={src}
          alt={alt}
          style={imageStyle}
          onError={() => setImageError(true)}
        />
      ) : (
        <span style={fallbackStyle}>{initials}</span>
      )}
    </div>
  )
})

export default Avatar
