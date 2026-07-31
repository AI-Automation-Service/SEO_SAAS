import { FileText } from 'lucide-react'

export function ContentTab() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
      <FileText size={36} className="mx-auto text-slate-300 mb-3" />
      <h3 className="font-display font-semibold text-slate-700 mb-1">Content</h3>
      <p className="text-slate-400 text-sm">Content generation coming in Phase 8</p>
    </div>
  )
}
