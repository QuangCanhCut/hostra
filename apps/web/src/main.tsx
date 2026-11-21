import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/styles/globals.css'
import { App } from '@/app/App'

async function enableMocking(): Promise<void> {
  const shouldMock =
    import.meta.env.DEV || import.meta.env.VITE_ENABLE_MSW !== 'false'

  if (!shouldMock) return

  const { worker } = await import('@/mocks/browser')
  await worker.start({
    onUnhandledRequest: 'bypass',
  })
}

enableMocking().then(() => {
  const rootEl = document.getElementById('root')
  if (!rootEl) return
  createRoot(rootEl).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
