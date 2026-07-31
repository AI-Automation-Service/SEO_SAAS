import { cn } from '@/lib/utils'
import { CheckCircle2, XCircle, Clock } from 'lucide-react'

type Status = 'connected' | 'error' | 'pending'

interface StatusBadgeProps {
  status: Status
  label?: string
  pulse?: boolean
}

const config: Record<Status, { icon: typeof CheckCircle2; color: string; bg: string; text: string }> = {
  connected: {
    icon: CheckCircle2,
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    text: 'Connected',
  },
  error: {
    icon: XCircle,
    color: 'text-red-600',
    bg: 'bg-red-50',
    text: 'Error',
  },
  pending: {
    icon: Clock,
    color: 'text-slate-400',
    bg: 'bg-slate-50',
    text: 'Not configured',
  },
}

export function StatusBadge({ status, label, pulse = false }: StatusBadgeProps) {
  const { icon: Icon, color, bg, text } = config[status]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
        bg,
        color
      )}
    >
      {pulse && status === 'connected' ? (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
        </span>
      ) : (
        <Icon size={12} />
      )}
      {label ?? text}
    </span>
  )
}
