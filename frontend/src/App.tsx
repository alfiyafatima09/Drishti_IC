import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
// import { LoginPage } from '@/features/auth/login/login-page'
import DashboardLayout from '@/features/dashboard/dashboard-layout'
import DashboardPage from '@/features/dashboard/dashboard-page'
import BatchPage from '@/features/dashboard/batch-page'
import ScanHistoryPage from '@/features/dashboard/scan-history-page'
import DashboardHome from '@/features/dashboard/dashboard-home'
import ScrapingPage from '@/features/scraping/scraping-page'
import ICDatabasePage from '@/features/ic-database/ic-database-page'
import './App.css'

function App() {
  return (
    <HashRouter>
      <Routes>
        {/* <Route path="/" element={<LoginPage />} /> */}
        <Route path="/" element={<Navigate to="/scan" replace />} />
        <Route path="/scan" element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
        <Route path="/batch" element={<DashboardLayout />}>
          <Route index element={<BatchPage />} />
        </Route>
        <Route path="/ic" element={<DashboardLayout />}>
          <Route index element={<ICDatabasePage />} />
        </Route>
        <Route path="/scrape" element={<DashboardLayout />}>
          <Route index element={<ScrapingPage />} />
        </Route>
        <Route path="/history" element={<DashboardLayout />}>
          <Route index element={<ScanHistoryPage />} />
        </Route>
        <Route path="/dashboard" element={<DashboardLayout />}>
          <Route index element={<DashboardHome />} />
        </Route>
        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/scan" replace />} />
      </Routes>
    </HashRouter>
  )
}

export default App
