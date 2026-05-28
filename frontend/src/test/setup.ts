/**
 * Vitest test setup file.
 * Configures the test environment for all frontend tests.
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { vi } from 'vitest'

// Mock import.meta.env for tests
vi.stubGlobal('import.meta.env', {
  VITE_API_BASE_URL: 'http://localhost:8000/api/v1',
})

// Mock localStorage
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem(key: string): string | null {
    return this.store[key] ?? null
  },
  setItem(key: string, value: string): void {
    this.store[key] = value
  },
  removeItem(key: string): void {
    delete this.store[key]
  },
  clear(): void {
    this.store = {}
  },
  get length(): number {
    return Object.keys(this.store).length
  },
  key(index: number): string | null {
    return Object.keys(this.store)[index] ?? null
  },
}

vi.stubGlobal('localStorage', localStorageMock)

// Reset localStorage between tests
beforeEach(() => {
  localStorageMock.clear()
})
