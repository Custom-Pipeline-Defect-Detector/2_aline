import React, { useState } from "react";
import { apiUpload } from "../app/api";

export default function Documents() {
  const [file, setFile] = useState<File | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function upload() {
    if (!file) return;
    setMsg("Uploading...");
    try {
      const res = await apiUpload("/documents/upload", file);
      setMsg(`Uploaded. doc_version_id=${res.doc_version_id}. Proposals will appear soon.`);
    } catch (e: any) {
      setMsg(String(e));
    }
  }

  return (
    <div>
      <div className="text-xl font-semibold mb-4">Documents</div>
      <div className="border rounded p-4 max-w-xl">
        <div className="text-sm text-gray-700 mb-2">Upload a document (PDF/DOCX/XLSX)</div>
        <input type="file" onChange={(e)=>setFile(e.target.files?.[0] || null)} />
        <button className="ml-3 px-3 py-1 border rounded" onClick={upload}>Upload</button>
        {msg && <div className="mt-3 text-sm">{msg}</div>}
        <div className="mt-3 text-xs text-gray-600">Also supported: drop files into C:\AlineInbox on the server.</div>
      </div>
    </div>
  );
}
