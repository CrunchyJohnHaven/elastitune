import { BrowserRouter } from 'react-router-dom'
import AppRoutes from './routes'
import ToastProvider from './components/ui/ToastProvider'
import ErrorBoundary from './components/ui/ErrorBoundary'

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
