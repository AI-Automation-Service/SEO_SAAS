import { BookOpen } from 'lucide-react'

const KNOWLEDGE_FILES = [
  'brand.md', 'business.md', 'products.md', 'services.md',
  'audience.md', 'competitors.md', 'tone.md', 'writing-guidelines.md',
  'seo-rules.md', 'faq.md', 'glossary.md', 'topic-map.md',
]

export function KnowledgeTab() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
      <BookOpen size={36} className="mx-auto text-slate-300 mb-3" />
      <h3 className="font-display font-semibold text-slate-700 mb-1">
        Knowledge Base
      </h3>
      <p className="text-slate-400 text-sm mb-6">
        Knowledge editing coming in Phase 4
      </p>
      <div className="flex flex-wrap gap-2 justify-center">
        {KNOWLEDGE_FILES.map((f) => (
          <span
            key={f}
            className="px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-full text-xs text-slate-500"
          >
            {f}
          </span>
        ))}
      </div>
    </div>
  )
}
