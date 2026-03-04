import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import Button from '../components/ui/Button';
import { apiFetch } from '../api';

interface QualityReportDetail {
  id: number;
  title: string;
  document_id: string;
  status: 'pending' | 'in_review' | 'approved' | 'rejected';
  created_at: string;
  updated_at: string;
  reviewer: string;
  score: number;
  details: {
    filename: string;
    file_size: number;
    content_type: string;
    extraction_accuracy: number;
    completeness_score: number;
    consistency_score: number;
  };
}

const QualityReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<QualityReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchQualityReport = async () => {
      try {
        const response = await apiFetch(`/quality/reports/${id}`);
        setReport(response as QualityReportDetail);
      } catch (err: any) {
        setError('Failed to load quality report');
        console.error('Quality report error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchQualityReport();
  }, [id]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-gray-100 text-gray-800';
      case 'in_review': return 'bg-blue-100 text-blue-800';
      case 'approved': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const handleBack = () => {
    navigate('/quality');
  };

  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Quality Report Detail</h1>
        <div className="text-center py-10">Loading report...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Quality Report Detail</h1>
        <Card className="p-6 text-center text-red-600">{error}</Card>
        <div className="mt-4">
          <Button onClick={handleBack}>Back to Quality Reports</Button>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Quality Report Detail</h1>
        <Card className="p-6 text-center">Report not found</Card>
        <div className="mt-4">
          <Button onClick={handleBack}>Back to Quality Reports</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Quality Report Detail</h1>
        <Button onClick={handleBack}>Back to Quality Reports</Button>
      </div>

      <Card className="p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h2 className="text-xl font-semibold mb-4">Report Information</h2>
            <div className="space-y-3">
              <div>
                <span className="font-medium">Title:</span> {report.title}
              </div>
              <div>
                <span className="font-medium">Document ID:</span> {report.document_id}
              </div>
              <div>
                <span className="font-medium">Status:</span>{' '}
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusClass(report.status)}`}>
                  {report.status.replace('_', ' ')}
                </span>
              </div>
              <div>
                <span className="font-medium">Score:</span> {report.score}/100
              </div>
              <div>
                <span className="font-medium">Created:</span> {formatDate(report.created_at)}
              </div>
              <div>
                <span className="font-medium">Updated:</span> {formatDate(report.updated_at)}
              </div>
              <div>
                <span className="font-medium">Reviewer:</span> {report.reviewer}
              </div>
            </div>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-4">Document Details</h2>
            <div className="space-y-3">
              <div>
                <span className="font-medium">Filename:</span> {report.details.filename}
              </div>
              <div>
                <span className="font-medium">File Size:</span> {(report.details.file_size / 1024).toFixed(2)} KB
              </div>
              <div>
                <span className="font-medium">Content Type:</span> {report.details.content_type}
              </div>
              <div>
                <span className="font-medium">Extraction Accuracy:</span> {(report.details.extraction_accuracy * 100).toFixed(1)}%
              </div>
              <div>
                <span className="font-medium">Completeness Score:</span> {(report.details.completeness_score * 100).toFixed(1)}%
              </div>
              <div>
                <span className="font-medium">Consistency Score:</span> {(report.details.consistency_score * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div className="flex space-x-4">
        <Button onClick={() => navigate(`/quality/report/${report.id}/edit`)}>Edit Report</Button>
        <Button variant="secondary" onClick={handleBack}>Back to Quality Reports</Button>
      </div>
    </div>
  );
};

export default QualityReportDetailPage;