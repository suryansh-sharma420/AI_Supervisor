interface Props {
  title: string
  action?: React.ReactNode
}

export function TopBar({ title, action }: Props) {
  return (
    <div className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-30">
      <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
      {action && <div>{action}</div>}
    </div>
  )
}
