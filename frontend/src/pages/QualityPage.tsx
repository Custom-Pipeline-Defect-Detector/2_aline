import React, { useState, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import Button from '../components/ui/Button';
import { apiFetch } from '../api';
import { useNavigate } from 'react-router-dom';

interface QualityReport {
  id: number;
  title: string;
  document_id: string;
  status: 'pending' | 'in_review' | 'approved' | 'rejected';
  created_at: string;
  updated_at: string;
  reviewer: string;
  score: number;
}

const QualityPage: React.FC = () => {
  const [reports, setReports] = useState<QualityReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_review' | 'approved' | 'rejected'>('all');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchQualityReports = async () => {
      try {
        const params = new URLSearchParams();
        if (filter !== 'all') {
          params.append('status', filter);
        }
        params.append('limit', '50');
        
        const response = await apiFetch(`/quality/reports?${params.toString()}`);
        setReports(response as QualityReport[]);
      } catch (err: any) {
        setError('Failed to load quality reports');
        console.error('Quality reports error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchQualityReports();
  }, [filter]);

  const filteredReports = filter === 'all' 
    ? reports 
    : reports.filter(report => report.status === filter);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
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

  const handleViewDetails = (reportId: number) => {
    navigate(`/quality/report/${reportId}`);
  };

  const handleEdit = (reportId: number) => {
    navigate(`/quality/report/${reportId}/edit`);
  };

  if (loading) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold mb-6">Automation Quality Control</h1>
        <div className="text-center py-10">Loading quality reports for automation projects...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Automation Quality Control</h1>
        <Card className="p-6 text-center text-red-600">{error}</Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Automation Quality Control</h1>
        <div className="flex space-x-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="border border-gray-300 rounded-md px-3 py-2 bg-white"
          >
            <option value="all">All Reports</option>
            <option value="pending">Pending</option>
            <option value="in_review">In Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
          <Button>New Report</Button>
        </div>
      </div>

      {filteredReports.length === 0 ? (
        <Card className="p-6 text-center text-gray-500">
          No quality reports found
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredReports.map((report) => (
            <Card key={report.id} className="p-4 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-semibold text-lg">{report.title}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusClass(report.status)}`}>
                      {report.status.replace('_', ' ')}
                    </span>
                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full">
                      Score: {report.score}/100
                    </span>
                  </div>
                  <div className="text-gray-600 mb-2">Document ID: {report.document_id}</div>
                  <div className="flex items-center text-sm text-gray-500">
                    <span>Reviewer: {report.reviewer}</span>
                    <span className="mx-2">•</span>
                    <span>Updated: {formatDate(report.updated_at)}</span>
                  </div>
                </div>
                <div className="flex space-x-2 ml-4">
                  <Button size="sm" onClick={() => handleViewDetails(report.id)}>View Details</Button>
                  <Button size="sm" variant="secondary" onClick={() => handleEdit(report.id)}>Edit</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 text-center">
          <div className="text-3xl font-bold text-blue-600">{reports.filter(r => r.status === 'pending').length}</div>
          <div className="text-gray-600 mt-2">Pending Reviews</div>
        </Card>
        <Card className="p-6 text-center">
          <div className="text-3xl font-bold text-yellow-600">{reports.filter(r => r.status === 'in_review').length}</div>
          <div className="text-gray-600 mt-2">In Review</div>
        </Card>
        <Card className="p-6 text-center">
          <div className="text-3xl font-bold text-green-600">{reports.filter(r => r.status === 'approved').length}</div>
          <div className="text-gray-600 mt-2">Approved</div>
        </Card>
      </div>
    </div>
  );
};

export default QualityPage;
