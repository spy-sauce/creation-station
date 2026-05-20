/**
 * UI Primitives Barrel Export
 * Per NUTRIENTS.md §B — Component Prop Contracts (frozen).
 *
 * Import components from this file:
 * import { Button, Input, Card, Avatar, Badge, Dialog, Spinner } from '@/components/ui'
 */

export { default as Button } from './button'
export { default as Input } from './input'
export { default as Card, CardHeader, CardContent, CardFooter } from './card'
export { default as Avatar } from './avatar'
export { default as Badge } from './badge'
export { default as Spinner } from './spinner'
export {
  default as Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogBody,
  DialogFooter,
} from './dialog'

// Type constants
export * from './types'
