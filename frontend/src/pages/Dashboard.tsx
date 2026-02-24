import React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../app/api";

export default function Dashboard() {
  const q = useQuery({ queryKey: ["dash"], queryFn: () => apiGet("/dashboard/summary") });
  if (q.isLoading) return <div>Loading...</div>;
  if (q.isError) return <div className="text-red-700">{String(q.error)}</div>;
  const d = q.data;
  const card = (label: string, value: any) => (
    <div className="border rounded p-4">
      <div className="text-sm text-gray-600">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
  return (
    <div>
      <div className="text-xl font-semibold mb-4">Dashboard</div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {card("Projects", d.projects)}
        {card("Open Tasks", d.tasks_open)}
        {card("Open Issues", d.issues_open)}
        {card("Open NCRs", d.ncrs_open)}
        {card("Pending Proposals", d.proposals_pending)}
      </div>
    </div>
  );
}
