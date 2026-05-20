/**
 * Shared type constants for UI primitives.
 * Per NUTRIENTS.md §B — Component Prop Contracts.
 *
 * This is the ONLY place these enums are defined on the frontend.
 */

/**
 * Button/component variant options.
 * @type {readonly ['default', 'primary', 'secondary', 'ghost', 'destructive', 'outline']}
 */
export const VARIANTS = ['default', 'primary', 'secondary', 'ghost', 'destructive', 'outline']

/**
 * Size options for components.
 * @type {readonly ['sm', 'md', 'lg']}
 */
export const SIZES = ['sm', 'md', 'lg']

/**
 * Card variant options.
 * @type {readonly ['default', 'elevated', 'outlined', 'flat']}
 */
export const CARD_VARIANTS = ['default', 'elevated', 'outlined', 'flat']

/**
 * Card padding options.
 * @type {readonly ['none', 'sm', 'md', 'lg']}
 */
export const CARD_PADDINGS = ['none', 'sm', 'md', 'lg']

/**
 * Avatar size options.
 * @type {readonly ['xs', 'sm', 'md', 'lg', 'xl']}
 */
export const AVATAR_SIZES = ['xs', 'sm', 'md', 'lg', 'xl']

/**
 * Avatar shape options.
 * @type {readonly ['circle', 'square']}
 */
export const AVATAR_SHAPES = ['circle', 'square']

/**
 * Badge variant options.
 * @type {readonly ['default', 'primary', 'success', 'warning', 'destructive']}
 */
export const BADGE_VARIANTS = ['default', 'primary', 'success', 'warning', 'destructive']

/**
 * Badge size options.
 * @type {readonly ['sm', 'md']}
 */
export const BADGE_SIZES = ['sm', 'md']

/**
 * Spinner size options.
 * @type {readonly ['sm', 'md', 'lg']}
 */
export const SPINNER_SIZES = ['sm', 'md', 'lg']
