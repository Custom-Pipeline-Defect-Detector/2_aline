import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../components/ui/Card';
import Input from '../components/ui/Input';
import { useDebounce } from 'use-debounce';

const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [debouncedQuery] = useDebounce(query, 500);
  const [results, setResults] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'documents' | 'customers' | 'projects' | 'proposals'>('all');

  const performSearch = useCallback(async () => {
    if (!debouncedQuery.trim()) {
      setResults({});
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      let apiUrl = '';
      if (activeTab === 'all') {
        apiUrl = `/search?q=${encodeURIComponent(debouncedQuery)}`;
      } else {
        apiUrl = `/search/${activeTab}?q=${encodeURIComponent(debouncedQuery)}`;
      }
      
      const token = localStorage.getItem('token');
      const response = await fetch(`/api${apiUrl}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error('Search error:', err);
      setError('Failed to perform search. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery, activeTab]);

  useEffect(() => {
    performSearch();
  }, [performSearch]);

  const renderResults = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center py-10">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-slate-600">Searching...</span>
        </div>
      );
    }

    if (error) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-red-700">{error}</p>
        </div>
      );
    }

    if (!debouncedQuery.trim()) {
      return (
        <div className="text-center py-10">
          <p className="text-slate-500">Enter a search term to get started</p>
        </div>
      );
    }

    if (activeTab === 'all') {
      if (!results.documents && !results.customers && !results.projects && !results.proposals) {
        return (
          <div className="text-center py-10">
            <p className="text-slate-500">No results found for "{debouncedQuery}"</p>
          </div>
        );
      }

      return (
        <div className="space-y-8">
          {/* Documents Results */}
          {results.documents && results.documents.length > 0 && (
            <div>
              <h3 className="text-xl font-semibold text-slate-900 mb-4">Documents ({results.counts?.documents || 0})</h3>
              <div className="space-y-3">
                {results.documents.map((doc: any) => (
                  <Card key={doc.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                    <div className="flex items-start">
                      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center mr-4">
                        <span className="text-blue-600">📄</span>
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-slate-900">{doc.filename}</h4>
                        <p className="text-sm text-slate-500 mt-1">
                          {doc.type} • {doc.processing_status} • {new Date(doc.created_at).toLocaleDateString()}
                        </p>
                        {doc.summary && (
                          <p className="text-sm text-slate-600 mt-2 line-clamp-2">{doc.summary}</p>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Customers Results */}
          {results.customers && results.customers.length > 0 && (
            <div>
              <h3 className="text-xl font-semibold text-slate-900 mb-4">Customers ({results.counts?.customers || 0})</h3>
              <div className="space-y-3">
                {results.customers.map((customer: any) => (
                  <Card key={customer.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-100 flex items-center justify-center mr-4">
                        <span className="text-green-600">👤</span>
                      </div>
                      <div>
                        <h4 className="font-medium text-slate-900">{customer.name}</h4>
                        <p className="text-sm text-slate-500">{customer.email} • {customer.company}</p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Projects Results */}
          {results.projects && results.projects.length > 0 && (
            <div>
              <h3 className="text-xl font-semibold text-slate-900 mb-4">Projects ({results.counts?.projects || 0})</h3>
              <div className="space-y-3">
                {results.projects.map((project: any) => (
                  <Card key={project.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center mr-4">
                        <span className="text-purple-600">📦</span>
                      </div>
                      <div>
                        <h4 className="font-medium text-slate-900">{project.name}</h4>
                        <p className="text-sm text-slate-500">{project.status} • {project.description}</p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Proposals Results */}
          {results.proposals && results.proposals.length > 0 && (
            <div>
              <h3 className="text-xl font-semibold text-slate-900 mb-4">Proposals ({results.counts?.proposals || 0})</h3>
              <div className="space-y-3">
                {results.proposals.map((proposal: any) => (
                  <Card key={proposal.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-yellow-100 flex items-center justify-center mr-4">
                        <span className="text-yellow-600">💡</span>
                      </div>
                      <div>
                        <h4 className="font-medium text-slate-900">{proposal.title}</h4>
                        <p className="text-sm text-slate-500">{proposal.status} • {proposal.description}</p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    } else {
      // Single category results
      const categoryResults = results;
      if (!categoryResults || categoryResults.length === 0) {
        return (
          <div className="text-center py-10">
            <p className="text-slate-500">No {activeTab} found for "{debouncedQuery}"</p>
          </div>
        );
      }

      if (activeTab === 'documents') {
        return (
          <div className="space-y-3">
            {categoryResults.map((doc: any) => (
              <Card key={doc.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                <div className="flex items-start">
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center mr-4">
                    <span className="text-blue-600">📄</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium text-slate-900">{doc.filename}</h4>
                    <p className="text-sm text-slate-500 mt-1">
                      {doc.type} • {doc.processing_status} • {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                    {doc.summary && (
                      <p className="text-sm text-slate-600 mt-2 line-clamp-2">{doc.summary}</p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        );
      } else if (activeTab === 'customers') {
        return (
          <div className="space-y-3">
            {categoryResults.map((customer: any) => (
              <Card key={customer.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                <div className="flex items-center">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-100 flex items-center justify-center mr-4">
                    <span className="text-green-600">👤</span>
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-900">{customer.name}</h4>
                    <p className="text-sm text-slate-500">{customer.email} • {customer.company}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        );
      } else if (activeTab === 'projects') {
        return (
          <div className="space-y-3">
            {categoryResults.map((project: any) => (
              <Card key={project.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                <div className="flex items-center">
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center mr-4">
                    <span className="text-purple-600">📦</span>
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-900">{project.name}</h4>
                    <p className="text-sm text-slate-500">{project.status} • {project.description}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        );
      } else if (activeTab === 'proposals') {
        return (
          <div className="space-y-3">
            {categoryResults.map((proposal: any) => (
              <Card key={proposal.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                <div className="flex items-center">
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-yellow-100 flex items-center justify-center mr-4">
                    <span className="text-yellow-600">💡</span>
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-900">{proposal.title}</h4>
                    <p className="text-sm text-slate-500">{proposal.status} • {proposal.description}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        );
      } else {
        return (
          <div className="text-center py-10">
            <p className="text-slate-500">Results for {activeTab} will appear here</p>
          </div>
        );
      }
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Automation Search</h1>
        <p className="text-slate-600 mt-2">Find automation development documents, clients, projects, and proposals</p>
      </div>

      <div className="mb-6">
        <Input
          type="text"
          placeholder="Search across all data..."
          value={query}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
          className="w-full max-w-2xl"
        />
      </div>

      {/* Search Tabs */}
      <div className="flex space-x-1 mb-6 bg-slate-100 p-1 rounded-xl w-fit">
        <button
          className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
            activeTab === 'all'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          onClick={() => setActiveTab('all')}
        >
          All ({results.counts?.documents + results.counts?.customers + results.counts?.projects + results.counts?.proposals || 0})
        </button>
        <button
          className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
            activeTab === 'documents'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          onClick={() => setActiveTab('documents')}
        >
          Documents ({results.counts?.documents || 0})
        </button>
        <button
          className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
            activeTab === 'customers'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          onClick={() => setActiveTab('customers')}
        >
          Customers ({results.counts?.customers || 0})
        </button>
        <button
          className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
            activeTab === 'projects'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          onClick={() => setActiveTab('projects')}
        >
          Projects ({results.counts?.projects || 0})
        </button>
        <button
          className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
            activeTab === 'proposals'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          onClick={() => setActiveTab('proposals')}
        >
          Proposals ({results.counts?.proposals || 0})
        </button>
      </div>

      {/* Search Results */}
      <Card className="p-0 overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">
            {debouncedQuery ? `Results for "${debouncedQuery}"` : 'Search Results'}
          </h2>
        </div>
        <div className="p-4">
          {renderResults()}
        </div>
      </Card>
    </div>
  );
};

export default SearchPage;