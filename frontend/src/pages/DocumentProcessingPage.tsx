import React, { useState, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import { useAuth } from '../auth/AuthContext';
import { useNotifications } from '../hooks/useNotifications';

interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
  status: string;
  progress: number;
  summary: string;
  processed_at?: string;
  metadata: Record<string, any>;
}

const DocumentProcessingPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState<Record<string, boolean>>({});
  const { user } = useAuth();
  const { addNotification } = useNotifications();

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await fetch('/api/document-processing/all');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      setDocuments(data.documents);
    } catch (error) {
      console.error('Error fetching documents:', error);
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to fetch documents'
      });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('/api/document-processing/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Upload result:', result);
        addNotification({
          type: 'success',
          title: 'Success',
          message: `File ${result.filename} uploaded successfully`
        });
        fetchDocuments(); // Refresh the document list
      } else {
        const errorText = await response.text();
        console.error('Upload failed:', errorText);
        addNotification({
          type: 'error',
          title: 'Upload Failed',
          message: `Failed to upload file: ${errorText}`
        });
      }
    } catch (error) {
      console.error('Upload error:', error);
      addNotification({
        type: 'error',
        title: 'Upload Error',
        message: 'An error occurred during upload'
      });
    } finally {
      setIsUploading(false);
      setSelectedFile(null);
    }
  };

  const handleProcess = async (documentId: string) => {
    setIsProcessing(prev => ({ ...prev, [documentId]: true }));

    try {
      const response = await fetch(`/api/document-processing/process/${documentId}`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Process result:', result);
        addNotification({
          type: 'success',
          title: 'Success',
          message: `File processed successfully`
        });
        fetchDocuments(); // Refresh the document list
      } else {
        const errorText = await response.text();
        console.error('Process failed:', errorText);
        addNotification({
          type: 'error',
          title: 'Processing Failed',
          message: `Failed to process file: ${errorText}`
        });
      }
    } catch (error) {
      console.error('Process error:', error);
      addNotification({
        type: 'error',
        title: 'Processing Error',
        message: 'An error occurred during processing'
      });
    } finally {
      setIsProcessing(prev => ({ ...prev, [documentId]: false }));
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100';
      case 'processing': return 'text-blue-600 bg-blue-100';
      case 'uploaded': return 'text-yellow-600 bg-yellow-100';
      case 'failed': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
    else return (bytes / 1048576).toFixed(2) + ' MB';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">File Processing</h1>
          <p className="text-gray-600 mt-2">Track and manage file processing workflows</p>
        </div>
      
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Upload File</h2>
        <div className="flex flex-col sm:flex-row gap-4 items-center">
          <Input
            type="file"
            onChange={handleFileChange}
            className="flex-1"
          />
          <Button onClick={handleUpload} disabled={!selectedFile || isUploading}>
            {isUploading ? 'Uploading...' : 'Upload File'}
          </Button>
        </div>
        <p className="text-sm text-slate-500 mt-2">Supported formats: PDF, DOCX, TXT, XLSX, PPTX</p>
      </Card>

      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Your Files</h2>
        <Button variant="secondary" onClick={fetchDocuments}>
            Refresh
          </Button>
        </div>
        {documents.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-slate-400 mb-4">📁</div>
            <p className="text-slate-600">No files uploaded yet.</p>
            <p className="text-sm text-slate-500 mt-2">Upload your first file to get started</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">File</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Size</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Progress</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Uploaded</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 bg-slate-100 rounded-lg flex items-center justify-center">
                          <span className="text-slate-600">{doc.file_type.toUpperCase()}</span>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-slate-900 truncate max-w-xs">{doc.filename}</div>
                          <div className="text-sm text-slate-500">{doc.summary.substring(0, 50)}{doc.summary.length > 50 ? '...' : ''}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{doc.file_type}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{formatFileSize(doc.file_size)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(doc.status)}`}>
                        {doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                      <div className="flex items-center">
                        <div className="w-24 bg-slate-200 rounded-full h-2 mr-2">
                          <div 
                            className={`h-2 rounded-full ${
                              doc.status === 'completed' ? 'bg-green-500' : 
                              doc.status === 'processing' ? 'bg-blue-500' : 
                              doc.status === 'failed' ? 'bg-red-500' : 'bg-yellow-500'
                            }`} 
                            style={{ width: `${doc.progress}%` }}
                          ></div>
                        </div>
                        <span>{doc.progress}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{formatDate(doc.uploaded_at)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                      <Button
                        onClick={() => handleProcess(doc.id)}
                        disabled={doc.status === 'processing' || doc.status === 'completed' || isProcessing[doc.id]}
                        variant={doc.status === 'uploaded' ? 'primary' : 'secondary'}
                      >
                        {isProcessing[doc.id] ? 'Processing...' : doc.status === 'completed' ? 'Processed' : 'Process'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

export default DocumentProcessingPage;