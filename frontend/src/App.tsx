import React from 'react';
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
import QualityReportDetailPage from './pages/QualityReportDetailPage';
import QualityReportEditPage from './pages/QualityReportEditPage';
import StatusPage from './pages/StatusPage'
import ForbiddenPage from './pages/ForbiddenPage'
import MessagesPage from './pages/MessagesPage'
import SearchPage from './pages/SearchPage'
import DocumentProcessingPage from './pages/DocumentProcessingPage';
import AiAssistantPage from './pages/AiAssistantPage';
import RequireRoles from './components/RequireRoles';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<ErrorBoundary><DashboardPage /></ErrorBoundary>} />
            <Route path="/inbox" element={<ErrorBoundary><InboxPage /></ErrorBoundary>} />
            <Route path="/documents" element={<ErrorBoundary><DocumentsPage /></ErrorBoundary>} />
            <Route path="/messages" element={<ErrorBoundary><MessagesPage /></ErrorBoundary>} />
            <Route path="/proposals" element={<ErrorBoundary><ProposalsPage /></ErrorBoundary>} />
            <Route path="/proposals/:id" element={<ErrorBoundary><ProposalDetailPage /></ErrorBoundary>} />
            <Route path="/projects" element={<ErrorBoundary><ProjectsPage /></ErrorBoundary>} />
            <Route path="/projects/:id" element={<ErrorBoundary><ProjectDetailPage /></ErrorBoundary>} />
            <Route path="/work" element={<ErrorBoundary><WorkPage /></ErrorBoundary>} />
            <Route path="/quality" element={<ErrorBoundary><QualityPage /></ErrorBoundary>} />
            <Route path="/quality/report/:id" element={<ErrorBoundary><QualityReportDetailPage /></ErrorBoundary>} />
            <Route path="/quality/report/:id/edit" element={<ErrorBoundary><QualityReportEditPage /></ErrorBoundary>} />
            <Route path="/customers" element={<ErrorBoundary><CustomersPage /></ErrorBoundary>} />
            <Route path="/customers/:id" element={<ErrorBoundary><CustomerDetailPage /></ErrorBoundary>} />
            <Route path="/search" element={<ErrorBoundary><SearchPage /></ErrorBoundary>} />
            <Route path="/processing" element={<ErrorBoundary><DocumentProcessingPage /></ErrorBoundary>} />
            <Route path="/ai-assistant" element={<ErrorBoundary><AiAssistantPage /></ErrorBoundary>} />
            <Route path="/status" element={<RequireRoles roles={["Admin", "Manager"]}><ErrorBoundary><StatusPage /></ErrorBoundary></RequireRoles>} />
          </Route>
        </Route>
        <Route path="/forbidden" element={<ForbiddenPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      <ToastContainer position="top-right" autoClose={5000} hideProgressBar={false} closeOnClick theme="light" />
    </div>
  )
}
