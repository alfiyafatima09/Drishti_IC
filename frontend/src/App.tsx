import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
// import { LoginPage } from '@/features/auth/login/login-page'
import DashboardLayout from '@/features/dashboard/dashboard-layout'
import DashboardPage from '@/features/dashboard/dashboard-page'
import ScrapingPage from '@/features/scraping/scraping-page'
import ICDatabasePage from '@/features/ic-database/ic-database-page'
import './App.css'

function App() {
  return (
    <HashRouter>
      <Routes>
        {/* <Route path="/" element={<LoginPage />} /> */}
        <Route path="/" element={<Navigate to="/scan" replace />} />
        <Route path="/dashboard" element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
        <Route path="/scan" element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
        <Route path="/ic" element={<DashboardLayout />}>
          <Route index element={<ICDatabasePage />} />
        </Route>
        <Route path="/scrape" element={<DashboardLayout />}>
          <Route index element={<ScrapingPage />} />
        </Route>
        <Route path="/database" element={<DashboardLayout />}>
          <Route index element={<ScrapingPage />} />
        </Route>
        <Route path="/history" element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/scan" replace />} />
      </Routes>
    </HashRouter>
  )
}

export default App
