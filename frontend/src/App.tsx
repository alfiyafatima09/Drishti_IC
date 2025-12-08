import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import DashboardLayout from '@/features/dashboard/dashboard-layout'
import DashboardPage from '@/features/dashboard/dashboard-page'
import ScrapingPage from '@/features/scraping/scraping-page'
import ICDatabasePage from '@/features/ic-database/ic-database-page'
import './App.css'

function App() {
  return (
    <HashRouter>
      <Routes>
        {/* New Scan - Home/Default page */}
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>

        {/* IC Database - Search & Browse */}
        <Route path="/database" element={<DashboardLayout />}>
          <Route index element={<ICDatabasePage />} />
        </Route>

        {/* Scrape & Manage - Data management */}
        <Route path="/manage" element={<DashboardLayout />}>
          <Route index element={<ScrapingPage />} />
        </Route>

        {/* Scan History */}
        <Route path="/history" element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>

        {/* Fallback - redirect to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  )
}

export default App
