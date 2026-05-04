import { useState } from 'react'

export default function SourceList({ sources, query, answer }) {
  const [saveState, setSaveState] = useState(null)

  if (!sources || sources.length === 0) return null

  const web = sources.filter(s => s.url)
  const docs = sources.filter(s => s.path)

  const saveToVault = async () => {
    setSaveState('saving')
    try {
      const r = await fetch('/api/vault/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, answer, sources })
      })
      if (r.ok) {
        const data = await r.json()
        setSaveState({ path: data.path, tags: data.tags, related: data.related })
      } else {
        const { detail } = await r.json()
        setSaveState({ error: detail })
      }
    } catch {
      setSaveState({ error: 'Request failed' })
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-stone-600 uppercase tracking-widest">Sources</div>
        {saveState === null && (
          <button
            onClick={saveToVault}
            className="text-xs text-stone-600 hover:text-accent transition-colors"
          >
            Save to vault
          </button>
        )}
        {saveState === 'saving' && (
          <span className="text-xs text-stone-600">Saving...</span>
        )}
        {saveState?.path && (
          <span className="text-xs text-emerald-600" title={saveState.tags?.join(', ')}>Saved</span>
        )}
        {saveState?.error && (
          <span className="text-xs text-red-500" title={saveState.error}>Failed</span>
        )}
      </div>

      <div className="space-y-1.5">
        {web.map((s, i) => (
          <a
            key={i}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-2.5 p-2.5 rounded-md bg-surface-2 hover:bg-surface-3 transition-colors group"
          >
            <span className="text-xs text-stone-700 mt-0.5 w-4 flex-shrink-0">{i + 1}</span>
            <div className="min-w-0">
              <div className="text-xs text-stone-400 group-hover:text-accent transition-colors leading-snug mb-0.5 line-clamp-2">
                {s.title || s.url}
              </div>
              <div className="text-xs text-stone-700 truncate">
                {(() => { try { return new URL(s.url).hostname } catch { return s.url } })()}
              </div>
            </div>
          </a>
        ))}
        {docs.map((s, i) => (
          <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-md bg-surface-2">
            <span className="text-xs text-accent mt-0.5 flex-shrink-0">◈</span>
            <div className="min-w-0">
              <div className="text-xs text-stone-400 leading-snug mb-0.5">{s.title}</div>
              <div className="text-xs text-stone-700 truncate font-mono">{s.path}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
