import { Card } from '../components/ui/Card'

export default function ForbiddenPage() {
  return (
    <Card className="p-6 text-center">
      <h1 className="text-lg font-semibold text-slate-900">You don&apos;t have access</h1>
      <p className="mt-2 text-sm text-slate-600">Your role does not allow this page. Contact an admin if you need access.</p>
    </Card>
  )
}
