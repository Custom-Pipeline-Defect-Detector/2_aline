import React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../app/api";
import { Link } from "react-router-dom";

export default function Proposals() {
  const q = useQuery({ queryKey:["proposals"], queryFn: ()=>apiGet("/proposals?status=pending") });
  if (q.isLoading) return <div>Loading...</div>;
  if (q.isError) return <div className="text-red-700">{String(q.error)}</div>;
  const rows = q.data as any[];
  return (
    <div>
      <div className="text-xl font-semibold mb-4">Pending Proposals</div>
      <div className="border rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-2">ID</th>
              <th className="text-left p-2">Table</th>
              <th className="text-left p-2">Action</th>
              <th className="text-left p-2">Status</th>
              <th className="text-left p-2">Open</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r=>(
              <tr key={r.id} className="border-t">
                <td className="p-2">{r.id}</td>
                <td className="p-2">{r.target_table}</td>
                <td className="p-2">{r.proposed_action}</td>
                <td className="p-2">{r.status}</td>
                <td className="p-2"><Link className="text-blue-700" to={`/proposals/${r.id}`}>Review</Link></td>
              </tr>
            ))}
            {rows.length===0 && <tr><td className="p-3 text-gray-600" colSpan={5}>No pending proposals yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
