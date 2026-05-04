const AGENT_LABELS = {
  supervisor: 'Supervisor',
  web_search: 'Web Search',
  docs: 'Personal Notes',
  synthesis: 'Synthesis',
  judge: 'Judge',
}

const AGENT_ICONS = {
  supervisor: '⬡',
  web_search: '◎',
  docs: '◈',
  synthesis: '◇',
  judge: '◆',
}

function StatusDot({ status }) {
  if (status === 'running') {
    return (
      <span className="inline-flex items-center justify-center w-4 h-4">
        <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
      </span>
    )
  }
  if (status === 'done') {
    return <span className="text-emerald-600 text-xs">✓</span>
  }
  if (status === 'error') {
    return <span className="text-red-500 text-xs">✗</span>
  }
  return null
}

export default function AgentFeed({ events }) {
  const agentEvents = events.filter(e => e.type === 'agent')

  if (agentEvents.length === 0) return null

  return (
    <div className="border border-surface-3 rounded-lg bg-surface-1 p-4 mb-6">
      <div className="text-xs text-stone-600 uppercase tracking-widest mb-3 font-medium">Working</div>
      <div className="space-y-2">
        {agentEvents.map((e, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="flex items-center gap-2 w-32 flex-shrink-0">
              <span className="text-accent text-xs">{AGENT_ICONS[e.name] || '○'}</span>
              <span className="text-xs text-stone-500">{AGENT_LABELS[e.name] || e.name}</span>
            </div>
            <StatusDot status={e.status} />
            {e.detail && (
              <span className="text-xs text-stone-600 truncate flex-1">{e.detail}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
