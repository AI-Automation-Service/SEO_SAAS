import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from '@/context/AuthContext'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Sidebar } from '@/components/layout/Sidebar'
import { cn } from '@/lib/utils'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { OnboardingPage } from '@/pages/OnboardingPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ProjectsPage } from '@/pages/ProjectsPage'
import { ProjectDetailPage } from '@/pages/ProjectDetailPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem('sidebar_collapsed') === 'true',
  )

  function toggleSidebar() {
    setSidebarCollapsed((prev) => {
      localStorage.setItem('sidebar_collapsed', String(!prev))
      return !prev
    })
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/onboarding"
              element={
                <ProtectedRoute>
                  <OnboardingPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <div className="flex h-screen bg-slate-50 overflow-hidden">
                    <Sidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
                    <main className={cn('flex-1 overflow-y-auto transition-all duration-200', sidebarCollapsed ? 'ml-14' : 'ml-60')}>
                      <Routes>
                        <Route path="/" element={<DashboardPage />} />
                        <Route path="/projects" element={<ProjectsPage />} />
                        <Route path="/projects/:name" element={<ProjectDetailPage />} />
                      </Routes>
                    </main>
                  </div>
                </ProtectedRoute>
              }
            />
          </Routes>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: { fontFamily: 'DM Sans, sans-serif', fontSize: '14px' },
            }}
          />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
