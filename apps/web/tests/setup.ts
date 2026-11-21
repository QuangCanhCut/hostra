import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll, vi } from 'vitest'
import { server } from '@/mocks/server'
import { resetStore } from '@/mocks/store'
import { resetM03Store } from '@/mocks/m03.store'

const storage = new Map<string, string>()
const memoryStorage: Storage = {
  get length() {
    return storage.size
  },
  clear: () => storage.clear(),
  getItem: (key: string) => storage.get(key) ?? null,
  key: (index: number) => Array.from(storage.keys())[index] ?? null,
  removeItem: (key: string) => {
    storage.delete(key)
  },
  setItem: (key: string, value: string) => {
    storage.set(key, String(value))
  },
}

Object.defineProperty(window, 'localStorage', {
  value: memoryStorage,
  writable: true,
})

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})

afterEach(() => {
  server.resetHandlers()
  resetStore('happy-path')
  resetM03Store('happy-path')
  memoryStorage.clear()
})

afterAll(() => {
  server.close()
})
