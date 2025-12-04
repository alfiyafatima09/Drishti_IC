import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { LoginPage } from '@/features/auth/login/login-page'
import DashboardLayout from '@/features/dashboard/dashboard-layout'
import DashboardPage from '@/features/dashboard/dashboard-page'
import './App.css'

function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/dashboard" element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
        <Route path="/scan" element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  )
}

export default App
