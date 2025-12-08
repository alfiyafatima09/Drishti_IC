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
        {/* Home/New Scan page - main entry point */}
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
        {/* Redirect /scan to home */}
        <Route path="/scan" element={<Navigate to="/" replace />} />
        <Route path="/dashboard" element={<DashboardLayout />}>
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
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  )
}

export default App
