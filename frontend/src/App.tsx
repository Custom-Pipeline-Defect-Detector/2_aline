import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import ErrorBoundary from './components/ErrorBoundary'
import RequireAuth from './components/RequireAuth'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import DocumentsPage from './pages/DocumentsPage'
import ProposalsPage from './pages/ProposalsPage'
import ProposalDetailPage from './pages/ProposalDetailPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import CustomersPage from './pages/CustomersPage'
import CustomerDetailPage from './pages/CustomerDetailPage'
import InboxPage from './pages/InboxPage'
import WorkPage from './pages/WorkPage'
import QualityPage from './pages/QualityPage'
import StatusPage from './pages/StatusPage'
import ForbiddenPage from './pages/ForbiddenPage'
import MessagesPage from './pages/MessagesPage'
import RequireRoles from './components/RequireRoles'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/inbox" replace />} />
          <Route path="/dashboard" element={<ErrorBoundary><DashboardPage /></ErrorBoundary>} />
          <Route path="/inbox" element={<RequireRoles roles={["Admin", "Manager", "PM", "Sales"]}><ErrorBoundary><InboxPage /></ErrorBoundary></RequireRoles>} />
          <Route path="/documents" element={<ErrorBoundary><DocumentsPage /></ErrorBoundary>} />
          <Route path="/messages" element={<ErrorBoundary><MessagesPage /></ErrorBoundary>} />
          <Route path="/proposals" element={<ErrorBoundary><ProposalsPage /></ErrorBoundary>} />
          <Route path="/proposals/:id" element={<ErrorBoundary><ProposalDetailPage /></ErrorBoundary>} />
          <Route path="/projects" element={<ErrorBoundary><ProjectsPage /></ErrorBoundary>} />
          <Route path="/projects/:id" element={<ErrorBoundary><ProjectDetailPage /></ErrorBoundary>} />
          <Route path="/work" element={<ErrorBoundary><WorkPage /></ErrorBoundary>} />
          <Route path="/quality" element={<ErrorBoundary><QualityPage /></ErrorBoundary>} />
          <Route path="/customers" element={<ErrorBoundary><CustomersPage /></ErrorBoundary>} />
          <Route path="/customers/:id" element={<ErrorBoundary><CustomerDetailPage /></ErrorBoundary>} />
          <Route path="/status" element={<RequireRoles roles={["Admin", "Manager"]}><ErrorBoundary><StatusPage /></ErrorBoundary></RequireRoles>} />
        </Route>
      </Route>
      <Route path="/forbidden" element={<ForbiddenPage />} />
      <Route path="*" element={<Navigate to="/inbox" replace />} />
    </Routes>
  )
}
