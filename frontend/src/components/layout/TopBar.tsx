interface TopBarProps {
  title: string
  subtitle?: string
  action?: React.ReactNode
}

export function TopBar({ title, subtitle, action }: TopBarProps) {
  return (
    <div className="h-16 flex items-center justify-between px-6 bg-white border-b border-slate-200">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 font-display leading-tight">
          {title}
        </h1>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
