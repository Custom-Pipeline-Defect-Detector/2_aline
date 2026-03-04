import React, { useState, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import Button from '../components/ui/Button';
import { apiFetch } from '../api';

interface InboxItem {
  id: number;
  title: string;
  description: string;
  type: 'document' | 'proposal' | 'project' | 'customer' | 'message';
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'processing' | 'completed' | 'reviewed';
  created_at: string;
  updated_at: string;
}

const InboxPage: React.FC = () => {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'pending' | 'processing' | 'completed' | 'reviewed'>('all');

  useEffect(() => {
    const fetchInboxItems = async () => {
      try {
        const data = await apiFetch('/inbox/items');
        setItems(data as InboxItem[]);
      } catch (err: any) {
        setError('Failed to load inbox items');
        console.error('Inbox error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchInboxItems();
  }, []);

  const filteredItems = filter === 'all' 
    ? items 
    : items.filter(item => item.status === filter);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getPriorityClass = (priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-gray-100 text-gray-800';
      case 'processing': return 'bg-blue-100 text-blue-800';
      case 'completed': return 'bg-green-100 text-green-800';
      case 'reviewed': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Automation Inbox</h1>
        <div className="text-center py-10">Loading inbox items...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Automation Inbox</h1>
        <Card className="p-6 text-center text-red-600">{error}</Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Automation Inbox</h1>
        <div className="flex space-x-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="border border-gray-300 rounded-md px-3 py-2 bg-white"
          >
            <option value="all">All Items</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="reviewed">Reviewed</option>
          </select>
          <Button onClick={() => window.location.reload()}>Refresh</Button>
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <Card className="p-6 text-center text-gray-500">
          No items in your inbox
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredItems.map((item) => (
            <Card key={item.id} className="p-4 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-semibold text-lg">{item.title}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityClass(item.priority)}`}>
                      {item.priority}
                    </span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusClass(item.status)}`}>
                      {item.status}
                    </span>
                  </div>
                  <p className="text-gray-600 mb-2">{item.description}</p>
                  <div className="flex items-center text-sm text-gray-500">
                    <span className="capitalize">{item.type}</span>
                    <span className="mx-2">•</span>
                    <span>Updated: {formatDate(item.updated_at)}</span>
                  </div>
                </div>
                <div className="flex space-x-2 ml-4">
                  <Button 
                    size="sm" 
                    onClick={() => {
                      // Navigate to the appropriate detail page based on item type
                      switch(item.type) {
                        case 'document':
                          window.location.href = `/documents/${item.id}`;
                          break;
                        case 'proposal':
                          window.location.href = `/proposals/${item.id}`;
                          break;
                        case 'project':
                          window.location.href = `/projects/${item.id}`;
                          break;
                        case 'customer':
                          window.location.href = `/customers/${item.id}`;
                          break;
                        case 'message':
                          window.location.href = `/messages/${item.id}`;
                          break;
                        default:
                          window.location.href = `/${item.type}s/${item.id}`;
                      }
                    }}
                  >
                    View
                  </Button>
                  <Button 
                    size="sm" 
                    variant="secondary"
                    onClick={() => {
                      // Process the item based on its type
                      console.log(`Processing item: ${item.id}`);
                      // Add processing logic here
                    }}
                  >
                    Process
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default InboxPage;