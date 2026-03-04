import { useState, useEffect } from 'react';
import { apiFetch } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import Button from './ui/Button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/Select';

interface User {
  id: number;
  name: string;
  email: string;
  role_name: string;
}

interface ProjectMember {
  id: number;
  user_id: number;
  project_id: number;
  project_role: string;
  engineer_type: string | null;
  report_to_user_id: number | null;
  assigned_by_user_id: number;
  user: User;
}

interface Project {
  id: number;
  name: string;
  project_code: string;
}

const ENGINEER_TYPES = [
  'plc_engineer',
  'software_engineer',
  'mechanical_engineer',
  'electrical_engineer',
  'hardware_engineer',
  'design_3d_engineer'
];

const PROJECT_ROLES = ['project_manager', 'lead_engineer', 'engineer'];

export default function ProjectTeamManagement({ projectId }: { projectId: number }) {
  const [projectMembers, setProjectMembers] = useState<ProjectMember[]>([]);
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Assignment states
  const [pmAssignment, setPmAssignment] = useState({ userId: '', loading: false });
  const [leadAssignment, setLeadAssignment] = useState({ engineerType: '', userId: '', loading: false });
  const [engineerAssignment, setEngineerAssignment] = useState({ userId: '', loading: false });

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  const loadProjectData = async () => {
    try {
      setLoading(true);
      const [members, users] = await Promise.all([
        apiFetch(`/projects/${projectId}/team`) as Promise<any[]>,
        apiFetch('/users') as Promise<User[]>
      ]);
      
      // Transform the API response to match our expected format
      const transformedMembers = members.map(member => ({
        id: member.id,
        user_id: member.user_id,
        project_id: projectId,
        project_role: member.project_role,
        engineer_type: member.engineer_type,
        report_to_user_id: member.report_to_user_id,
        assigned_by_user_id: member.assigned_by_user_id,
        user: {
          id: member.user_id,
          name: member.user_name,
          email: member.user_email,
          role_name: '' // Not provided in team response
        }
      }));
      setProjectMembers(transformedMembers);
      setAvailableUsers(users);
    } catch (err) {
      setError('Failed to load project team data');
    } finally {
      setLoading(false);
    }
  };

  const assignProjectManager = async () => {
    if (!pmAssignment.userId) return;

    try {
      setPmAssignment({ ...pmAssignment, loading: true });
      await apiFetch(`/projects/${projectId}/assign-pm`, {
        method: 'POST',
        body: JSON.stringify({ pm_user_id: parseInt(pmAssignment.userId) })
      });
      await loadProjectData();
      setPmAssignment({ userId: '', loading: false });
    } catch (err) {
      setError('Failed to assign project manager');
    }
  };

  const assignLeadEngineer = async () => {
    if (!leadAssignment.engineerType || !leadAssignment.userId) return;

    try {
      setLeadAssignment({ ...leadAssignment, loading: true });
      await apiFetch(`/projects/${projectId}/assign-lead`, {
        method: 'POST',
        body: JSON.stringify({
          engineer_type: leadAssignment.engineerType,
          lead_user_id: parseInt(leadAssignment.userId)
        })
      });
      await loadProjectData();
      setLeadAssignment({ engineerType: '', userId: '', loading: false });
    } catch (err) {
      setError('Failed to assign lead engineer');
    }
  };

  const addEngineerToProject = async () => {
    if (!engineerAssignment.userId) return;

    try {
      setEngineerAssignment({ ...engineerAssignment, loading: true });
      await apiFetch(`/projects/${projectId}/add-engineer`, {
        method: 'POST',
        body: JSON.stringify({ engineer_user_id: parseInt(engineerAssignment.userId) })
      });
      await loadProjectData();
      setEngineerAssignment({ userId: '', loading: false });
    } catch (err) {
      setError('Failed to add engineer to project');
    }
  };

  const getProjectManager = () => projectMembers.find(m => m.project_role === 'project_manager');
  const getLeadEngineers = () => projectMembers.filter(m => m.project_role === 'lead_engineer');
  const getEngineers = () => projectMembers.filter(m => m.project_role === 'engineer');

  if (loading) {
    return <Card><CardContent><p>Loading project team...</p></CardContent></Card>;
  }

  return (
    <div className="space-y-6">
      {error && <div className="text-red-600 text-sm">{error}</div>}

      {/* Project Manager Assignment */}
      <Card>
        <CardHeader>
          <CardTitle>Project Manager</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              {getProjectManager() ? (
                <div className="text-sm">
                  <strong>{getProjectManager()?.user.name}</strong> ({getProjectManager()?.user.email})
                </div>
              ) : (
                <div className="text-sm text-gray-500">No Project Manager assigned</div>
              )}
            </div>
            <div className="flex gap-2">
              <Select value={pmAssignment.userId} onValueChange={(value: string) => setPmAssignment({...pmAssignment, userId: value})}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Select PM" />
                </SelectTrigger>
                <SelectContent>
                  {availableUsers
                    .filter(user => user.role_name === 'Manager' || user.role_name === 'PM')
                    .map(user => (
                      <SelectItem key={user.id} value={user.id.toString()}>
                        {user.name} ({user.email})
                      </SelectItem>
                    ))
                  }
                </SelectContent>
              </Select>
              <Button onClick={assignProjectManager} disabled={pmAssignment.loading || !pmAssignment.userId}>
                {pmAssignment.loading ? 'Assigning...' : 'Assign PM'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Lead Engineers Assignment */}
      <Card>
        <CardHeader>
          <CardTitle>Lead Engineers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {getLeadEngineers().map(lead => (
            <div key={lead.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div>
                <strong>{lead.user.name}</strong> - {lead.engineer_type} ({lead.user.email})
              </div>
            </div>
          ))}
          
          <div className="flex gap-2 pt-2">
            <Select value={leadAssignment.engineerType} onValueChange={(value: string) => setLeadAssignment({...leadAssignment, engineerType: value})}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                {ENGINEER_TYPES.map(type => (
                  <SelectItem key={type} value={type}>
                    {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={leadAssignment.userId} onValueChange={(value: string) => setLeadAssignment({...leadAssignment, userId: value})}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select Lead" />
              </SelectTrigger>
              <SelectContent>
                {availableUsers
                  .filter(user => user.role_name === 'Engineer')
                  .map(user => (
                    <SelectItem key={user.id} value={user.id.toString()}>
                      {user.name} ({user.email})
                    </SelectItem>
                  ))
                }
              </SelectContent>
            </Select>
            <Button onClick={assignLeadEngineer} disabled={leadAssignment.loading || !leadAssignment.engineerType || !leadAssignment.userId}>
              {leadAssignment.loading ? 'Assigning...' : 'Assign Lead'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Engineers Assignment */}
      <Card>
        <CardHeader>
          <CardTitle>Engineers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {getEngineers().map(engineer => (
            <div key={engineer.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div>
                <strong>{engineer.user.name}</strong> - {engineer.engineer_type} ({engineer.user.email})
                {engineer.report_to_user_id && (
                  <div className="text-xs text-gray-500">Reports to: {projectMembers.find(m => m.id === engineer.report_to_user_id)?.user.name}</div>
                )}
              </div>
            </div>
          ))}
          
          <div className="flex gap-2 pt-2">
            <Select value={engineerAssignment.userId} onValueChange={(value: string) => setEngineerAssignment({...engineerAssignment, userId: value})}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select Engineer" />
              </SelectTrigger>
              <SelectContent>
                {availableUsers
                  .filter(user => user.role_name === 'Engineer')
                  .map(user => (
                    <SelectItem key={user.id} value={user.id.toString()}>
                      {user.name} ({user.email})
                    </SelectItem>
                  ))
                }
              </SelectContent>
            </Select>
            <Button onClick={addEngineerToProject} disabled={engineerAssignment.loading || !engineerAssignment.userId}>
              {engineerAssignment.loading ? 'Adding...' : 'Add Engineer'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
