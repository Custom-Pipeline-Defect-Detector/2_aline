import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "../app/api";

export default function ProposalDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const q = useQuery({ queryKey:["proposal", id], queryFn: ()=>apiGet(`/proposals/${id}`) });
  const [saving, setSaving] = useState(false);
  const [reason, setReason] = useState("");

  if (q.isLoading) return <div>Loading...</div>;
  if (q.isError) return <div className="text-red-700">{String(q.error)}</div>;

  const p = q.data as any;
  const [fields, setFields] = useState<any>(p.proposed_fields || {});
  const conf = p.field_confidence || {};
  const ev = p.evidence || {};

  async function approve() {
    setSaving(true);
    try {
      await apiPost(`/proposals/${id}/approve`, { proposed_fields: fields });
      nav("/proposals");
    } finally {
      setSaving(false);
    }
  }
  async function reject() {
    setSaving(true);
    try {
      await apiPost(`/proposals/${id}/reject`, { reason });
      nav("/proposals");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="text-xl font-semibold mb-2">Proposal #{p.id}</div>
      <div className="text-sm text-gray-600 mb-4">{p.target_table} / {p.proposed_action} / {p.status}</div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="border rounded p-3">
          <div className="font-semibold mb-2">Proposed Fields (editable)</div>
          {Object.keys(fields).length === 0 && <div className="text-sm text-gray-600">No fields</div>}
          <div className="flex flex-col gap-2">
            {Object.entries(fields).map(([k,v])=>(
              <div key={k} className="border rounded p-2">
                <div className="flex justify-between">
                  <div className="font-mono text-xs">{k}</div>
                  <div className="text-xs text-gray-600">conf: {Math.round(((conf as any)[k] ?? 0)*100)}%</div>
                </div>
                <input className="border p-2 rounded w-full mt-1" value={(v as any) ?? ""} onChange={e=>setFields({...fields, [k]: e.target.value})}/>
                {(ev as any)[k]?.snippet && (
                  <div className="mt-2 text-xs">
                    <div className="text-gray-500">Evidence:</div>
                    <div className="bg-gray-50 border rounded p-2">{(ev as any)[k].snippet}</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="border rounded p-3">
          <div className="font-semibold mb-2">Actions</div>
          <button disabled={saving} className="px-3 py-2 bg-green-700 text-white rounded mr-2" onClick={approve}>Approve</button>
          <div className="mt-4">
            <div className="text-sm mb-1">Reject reason (optional)</div>
            <input className="border p-2 rounded w-full" value={reason} onChange={e=>setReason(e.target.value)} />
            <button disabled={saving} className="mt-2 px-3 py-2 bg-red-700 text-white rounded" onClick={reject}>Reject</button>
          </div>
        </div>
      </div>
    </div>
  );
}
