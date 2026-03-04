import React from "react";
import { Routes, Route, Link, useNavigate } from "react-router-dom";
import Login from "../pages/Login";
import Dashboard from "../pages/Dashboard";
import Documents from "../pages/Documents";
import Proposals from "../pages/Proposals";
import ProposalDetail from "../pages/ProposalDetail";
import Projects from "../pages/Projects";
import ProjectDetail from "../pages/ProjectDetail";
import { getToken } from "./api";

function Nav() {
  const nav = useNavigate();
  const token = getToken();
  return (
    <div className="border-b p-3 flex gap-4 items-center">
      <div className="font-semibold">AutoDev Automation Platform</div>
      {token && (
        <>
          <Link to="/dashboard" className="text-blue-700">Dashboard</Link>
          <Link to="/documents" className="text-blue-700">Documents</Link>
          <Link to="/proposals" className="text-blue-700">Proposals</Link>
          <Link to="/projects" className="text-blue-700">Projects</Link>
          <button className="ml-auto px-3 py-1 border rounded" onClick={() => { localStorage.removeItem("token"); nav("/"); }}>
            Logout
          </button>
        </>
      )}
    </div>
  );
}

export default function App() {
  return (
    <div className="min-h-screen">
      <Nav />
      <div className="p-4">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/proposals" element={<Proposals />} />
          <Route path="/proposals/:id" element={<ProposalDetail />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
        </Routes>
      </div>
    </div>
  );
}
