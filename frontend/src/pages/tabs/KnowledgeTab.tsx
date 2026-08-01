import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Save, Clock } from 'lucide-react'
import toast from 'react-hot-toast'
import { knowledgeApi, getErrorMessage } from '@/api/client'

interface KnowledgeTabProps {
  projectName: string
}

const SECTIONS = [
  {
    key: 'about' as const,
    label: 'About the Business',
    placeholder:
      'Describe your business — what you do, how long you\'ve been operating, key achievements, and what makes you different from competitors.',
  },
  {
    key: 'products_services' as const,
    label: 'Products & Services',
    placeholder:
      'List your main products or services. Include pricing tiers, key features, and what problems each solves for customers.',
  },
  {
    key: 'target_audience' as const,
    label: 'Target Audience',
    placeholder:
      'Describe your ideal customer — demographics, pain points, goals, where they spend time online, and what motivates them to buy.',
  },
  {
    key: 'brand_voice' as const,
    label: 'Brand Voice & Tone',
    placeholder:
      'How do you communicate? (e.g., professional but friendly, authoritative, casual, humorous) Include words you use often and words to avoid.',
  },
  {
    key: 'competitors_notes' as const,
    label: 'Competitor Notes',
    placeholder:
      'Who are your main competitors? What do they do well? Where do they fall short? What angles or positioning do you want to contrast against them?',
  },
  {
    key: 'seo_context' as const,
    label: 'SEO Context',
    placeholder:
      'Any specific SEO guidance — content pillars you\'ve committed to, topics to avoid, seasonal patterns, local SEO focus, or existing pages that are performing well.',
  },
] as const

type FieldKey = (typeof SECTIONS)[number]['key']

type FormState = Record<FieldKey, string>

const EMPTY: FormState = {
  about: '',
  products_services: '',
  target_audience: '',
  brand_voice: '',
  competitors_notes: '',
  seo_context: '',
}

export function KnowledgeTab({ projectName }: KnowledgeTabProps) {
  const qc = useQueryClient()
  const [form, setForm] = useState<FormState>(EMPTY)

  const { data, isLoading } = useQuery({
    queryKey: ['knowledge', projectName],
    queryFn: () => knowledgeApi.get(projectName),
  })

  useEffect(() => {
    if (!data) return
    setForm({
      about: data.about ?? '',
      products_services: data.products_services ?? '',
      target_audience: data.target_audience ?? '',
      brand_voice: data.brand_voice ?? '',
      competitors_notes: data.competitors_notes ?? '',
      seo_context: data.seo_context ?? '',
    })
  }, [data])

  const { mutate: save, isPending } = useMutation({
    mutationFn: () => knowledgeApi.save(projectName, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge', projectName] })
      toast.success('Knowledge base saved')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const isDirty =
    data !== undefined &&
    SECTIONS.some((s) => form[s.key] !== (data[s.key] ?? ''))

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <p className="text-slate-400 text-sm">Loading knowledge base...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 px-6 py-4 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center shrink-0">
            <BookOpen size={18} className="text-indigo-500" />
          </div>
          <div>
            <h2 className="font-display font-semibold text-slate-900 text-sm">Knowledge Base</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              This context is injected into every AI agent — the richer it is, the more specific the output.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {data?.updated_at && (
            <span className="flex items-center gap-1 text-xs text-slate-400">
              <Clock size={11} />
              Saved {new Date(data.updated_at).toLocaleDateString()}
            </span>
          )}
          <button
            type="button"
            onClick={() => save()}
            disabled={isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
          >
            <Save size={14} />
            {isPending ? 'Saving...' : isDirty ? 'Save changes' : 'Save'}
          </button>
        </div>
      </div>

      {/* Sections */}
      <div className="grid grid-cols-1 gap-4">
        {SECTIONS.map((section) => (
          <div key={section.key} className="bg-white rounded-xl border border-slate-200 p-5">
            <label
              htmlFor={`kb-${section.key}`}
              className="block font-medium text-sm text-slate-800 mb-2"
            >
              {section.label}
            </label>
            <textarea
              id={`kb-${section.key}`}
              rows={5}
              value={form[section.key]}
              onChange={(e) => setForm((f) => ({ ...f, [section.key]: e.target.value }))}
              placeholder={section.placeholder}
              className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent resize-y leading-relaxed"
            />
          </div>
        ))}
      </div>

      {/* Bottom save */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => save()}
          disabled={isPending}
          className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
        >
          <Save size={14} />
          {isPending ? 'Saving...' : 'Save knowledge base'}
        </button>
      </div>
    </div>
  )
}
