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

const QualityReportEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<QualityReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    status: 'pending' as 'pending' | 'in_review' | 'approved' | 'rejected',
    score: 0,
    comment: ''
  });

  useEffect(() => {
    const fetchQualityReport = async () => {
      try {
        const response = await apiFetch(`/quality/reports/${id}`);
        const data = response as QualityReportDetail;
        setReport(data);
        setFormData({
          status: data.status,
          score: data.score,
          comment: ''
        });
      } catch (err: any) {
        setError('Failed to load quality report');
        console.error('Quality report error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchQualityReport();
  }, [id]);

  const handleInputChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'score' ? Number(value) : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      // Submit the quality review to the backend
      const response = await apiFetch(`/quality/reports/${id}/review`, {
        method: 'POST',
        body: JSON.stringify({
          status: formData.status,
          score: formData.score,
          comment: formData.comment
        })
      });
      
      console.log('Review submitted:', response);
      alert('Quality report updated successfully!');
      navigate(`/quality/report/${id}`);
    } catch (err: any) {
      setError('Failed to update quality report');
      console.error('Update error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    navigate(`/quality/report/${id}`);
  };

  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Edit Quality Report</h1>
        <div className="text-center py-10">Loading report...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Edit Quality Report</h1>
        <Card className="p-6 text-center text-red-600">{error}</Card>
        <div className="mt-4">
          <Button onClick={() => navigate('/quality')}>Back to Quality Reports</Button>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Edit Quality Report</h1>
        <Card className="p-6 text-center">Report not found</Card>
        <div className="mt-4">
          <Button onClick={() => navigate('/quality')}>Back to Quality Reports</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Edit Quality Report</h1>
        <Button onClick={handleCancel} variant="secondary">Cancel</Button>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h2 className="text-xl font-semibold mb-4">Report Information</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <div className="text-gray-900">{report.title}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Document ID</label>
                  <div className="text-gray-900">{report.document_id}</div>
                </div>
                <div>
                  <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
                    Status
                  </label>
                  <select
                    id="status"
                    name="status"
                    value={formData.status}
                    onChange={handleInputChange}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  >
                    <option value="pending">Pending</option>
                    <option value="in_review">In Review</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="score" className="block text-sm font-medium text-gray-700 mb-1">
                    Quality Score (0-100)
                  </label>
                  <input
                    type="number"
                    id="score"
                    name="score"
                    min="0"
                    max="100"
                    value={formData.score}
                    onChange={handleInputChange}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  />
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

        <Card className="p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Review Comment</h2>
          <textarea
            name="comment"
            value={formData.comment}
            onChange={handleInputChange}
            rows={4}
            className="w-full border border-gray-300 rounded-md px-3 py-2"
            placeholder="Add your review comment here..."
          />
        </Card>

        <div className="flex space-x-4">
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
          <Button type="button" variant="secondary" onClick={handleCancel}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
};

export default QualityReportEditPage;