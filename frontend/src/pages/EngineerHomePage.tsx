import { Card } from '../components/ui/Card'

export default function EngineerHomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Engineering Dashboard</h1>
        <p className="text-sm text-slate-500">Access specialized engineering tools and resources.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="p-6">
          <div className="text-2xl mb-2">🔧</div>
          <h3 className="font-semibold text-slate-900 mb-1">Project Management</h3>
          <p className="text-sm text-slate-500">Manage engineering projects and track progress.</p>
        </Card>

        <Card className="p-6">
          <div className="text-2xl mb-2">⚙️</div>
          <h3 className="font-semibold text-slate-900 mb-1">Work Orders</h3>
          <p className="text-sm text-slate-500">Create and manage engineering work orders.</p>
        </Card>

        <Card className="p-6">
          <div className="text-2xl mb-2">🧪</div>
          <h3 className="font-semibold text-slate-900 mb-1">Quality Control</h3>
          <p className="text-sm text-slate-500">Monitor and report quality metrics.</p>
        </Card>

        <Card className="p-6">
          <div className="text-2xl mb-2">📋</div>
          <h3 className="font-semibold text-slate-900 mb-1">Documentation</h3>
          <p className="text-sm text-slate-500">Access engineering documents and specifications.</p>
        </Card>

        <Card className="p-6">
          <div className="text-2xl mb-2">💬</div>
          <h3 className="font-semibold text-slate-900 mb-1">Communication</h3>
          <p className="text-sm text-slate-500">Collaborate with team members.</p>
        </Card>

        <Card className="p-6">
          <div className="text-2xl mb-2">🤖</div>
          <h3 className="font-semibold text-slate-900 mb-1">Automation Tools</h3>
          <p className="text-sm text-slate-500">Access specialized automation development tools.</p>
        </Card>
      </div>

      <Card className="p-6">
        <h3 className="font-semibold text-slate-900 mb-3">Recent Activity</h3>
        <div className="space-y-3">
          <div className="flex items-start gap-3 text-sm">
            <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5"></div>
            <div>
              <p className="font-medium">New project created: "Pipeline Optimization"</p>
              <p className="text-slate-500">2 hours ago</p>
            </div>
          </div>
          <div className="flex items-start gap-3 text-sm">
            <div className="w-2 h-2 rounded-full bg-amber-500 mt-1.5"></div>
            <div>
              <p className="font-medium">Quality report submitted: "Q4 Review"</p>
              <p className="text-slate-500">5 hours ago</p>
            </div>
          </div>
          <div className="flex items-start gap-3 text-sm">
            <div className="w-2 h-2 rounded-full bg-sky-500 mt-1.5"></div>
            <div>
              <p className="font-medium">Work order completed: "System Upgrade"</p>
              <p className="text-slate-500">Yesterday</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}