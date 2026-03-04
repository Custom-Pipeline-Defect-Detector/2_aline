import React, { useState, useEffect } from 'react';
import { Card } from './ui/Card';
import Button from './ui/Button';

interface DocumentUploadTrackerProps {
  documentId?: string;
  onStatusUpdate?: (status: string, progress: number) => void;
}

const DocumentUploadTracker: React.FC<DocumentUploadTrackerProps> = ({ 
  documentId, 
  onStatusUpdate 
}) => {
  const [status, setStatus] = useState<string>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  // Simulate status updates
  useEffect(() => {
    if (!documentId) return;

    const fetchStatus = async () => {
      try {
        const response = await fetch(`/api/document-processing/status/${documentId}`);
        const data = await response.json();
        
        setStatus(data.status);
        setProgress(data.progress);
        
        if (onStatusUpdate) {
          onStatusUpdate(data.status, data.progress);
        }
        
        // Continue polling if still processing
        if (data.status === 'processing' || data.status === 'uploading') {
          setTimeout(fetchStatus, 2000); // Poll every 2 seconds
        }
      } catch (error) {
        console.error('Error fetching asset status:', error);
      }
    };

    // Start polling when we have a document ID
    if (documentId) {
      fetchStatus();
    }
  }, [documentId, onStatusUpdate]);

  const handleProcessDocument = async () => {
    if (!documentId) return;

    try {
      setIsProcessing(true);
      const response = await fetch(`/api/document-processing/process/${documentId}`, {
        method: 'POST',
      });
      
      const data = await response.json();
      console.log('Processing triggered:', data);
      
      // Reset and start polling again
      setStatus('processing');
      setProgress(0);
    } catch (error) {
      console.error('Error triggering asset processing:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Status badge styling
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'uploading':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-900">Asset Processing Status</h3>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusStyle(status)}`}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </span>
      </div>
      
      <div className="mb-4">
        <div className="flex justify-between text-sm text-slate-600 mb-1">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-in-out" 
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>
      
      <div className="text-sm text-slate-600 mb-4">
        {status === 'idle' && 'No asset selected'}
        {status === 'uploading' && 'Uploading asset to server...'}
        {status === 'processing' && 'Processing asset with AI agents...'}
        {status === 'completed' && 'Asset processing completed successfully!'}
        {status === 'failed' && 'Asset processing failed. Please try again.'}
      </div>
      
      {status !== 'completed' && (
        <Button 
          onClick={handleProcessDocument} 
          disabled={isProcessing || status === 'processing'}
          className="w-full"
        >
          {isProcessing ? 'Processing...' : status === 'processing' ? 'Processing...' : 'Start Processing'}
        </Button>
      )}
    </Card>
  );
};

export default DocumentUploadTracker;