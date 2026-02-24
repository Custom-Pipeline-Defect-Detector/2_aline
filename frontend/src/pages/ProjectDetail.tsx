import React from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../app/api";

export default function ProjectDetail() {
  const { id } = useParams();
  const q = useQuery({ queryKey:["project", id], queryFn: ()=>apiGet(`/projects/${id}`) });
  if (q.isLoading) return <div>Loading...</div>;
  if (q.isError) return <div className="text-red-700">{String(q.error)}</div>;
  const d = q.data as any;
  return (
    <div>
      <div className="text-xl font-semibold mb-2">Project</div>
      <div className="border rounded p-3 mb-4">
        <div><span className="text-gray-600 text-sm">Code:</span> {d.project.project_code || "-"}</div>
        <div><span className="text-gray-600 text-sm">Name:</span> {d.project.name || "-"}</div>
        <div><span className="text-gray-600 text-sm">Status:</span> {d.project.status}</div>
      </div>
      <div className="grid md:grid-cols-3 gap-3">
        <div className="border rounded p-3">
          <div className="font-semibold mb-2">Tasks</div>
          <ul className="text-sm list-disc pl-5">
            {d.tasks.map((t:any)=>(<li key={t.id}>{t.title} <span className="text-gray-500">({t.status})</span></li>))}
            {d.tasks.length===0 && <div className="text-gray-600 text-sm">None</div>}
          </ul>
        </div>
        <div className="border rounded p-3">
          <div className="font-semibold mb-2">Issues</div>
          <ul className="text-sm list-disc pl-5">
            {d.issues.map((i:any)=>(<li key={i.id}>{i.severity}: {i.description}</li>))}
            {d.issues.length===0 && <div className="text-gray-600 text-sm">None</div>}
          </ul>
        </div>
        <div className="border rounded p-3">
          <div className="font-semibold mb-2">NCRs</div>
          <ul className="text-sm list-disc pl-5">
            {d.ncrs.map((n:any)=>(<li key={n.id}>{n.description} <span className="text-gray-500">({n.status})</span></li>))}
            {d.ncrs.length===0 && <div className="text-gray-600 text-sm">None</div>}
          </ul>
        </div>
      </div>
    </div>
  );
}
