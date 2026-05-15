import { useEffect, useRef, useState } from 'react'

export default function Sidebar({ activeId, onSelect, onNew, onDeleted }) {
  const [history, setHistory] = useState([])
  const [search, setSearch] = useState('')
  const searchRef = useRef(null)

  useEffect(() => {
    fetch('/api/history')
      .then(r => r.json())
      .then(setHistory)
      .catch(() => {})
  }, [activeId])

  const onDelete = async (id) => {
    await fetch(`/api/history/${id}`, { method: 'DELETE' })
    setHistory(prev => prev.filter(s => s.id !== id))
    if (id === activeId) onDeleted()
  }

  const filtered = search.trim()
    ? history.filter(s => s.query.toLowerCase().includes(search.toLowerCase()))
    : history

  const grouped = filtered.reduce((acc, s) => {
    const date = new Date(s.created_at + 'Z').toLocaleDateString('en-US', {
      month: 'short', day: 'numeric'
    })
    if (!acc[date]) acc[date] = []
    acc[date].push(s)
    return acc
  }, {})

  return (
    <div className="w-60 flex-shrink-0 flex flex-col bg-surface-1 border-r border-surface-3 h-screen">
      <div className="p-4 border-b border-surface-3">
        <div className="flex items-center gap-2.5 mb-5">
          <div className="w-5 h-5 rounded bg-accent/20 border border-accent/30 flex items-center justify-center">
            <span className="text-accent text-xs font-semibold">N</span>
          </div>
          <span className="font-semibold text-sm tracking-widest text-stone-300 uppercase">Nexus</span>
        </div>
        <button
          onClick={onNew}
          className="w-full py-2 px-3 rounded-md border border-surface-4 hover:border-accent/30 text-sm text-left text-stone-500 hover:text-stone-300 transition-colors mb-3"
        >
          + New research
        </button>
        <input
          ref={searchRef}
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search history..."
          className="w-full bg-surface-2 border border-surface-3 rounded-md px-3 py-1.5 text-xs text-stone-400 placeholder-stone-700 focus:outline-none focus:border-accent/50 transition-colors"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {Object.entries(grouped).map(([date, sessions]) => (
          <div key={date} className="mb-4">
            <div className="text-xs text-stone-700 px-2 py-1 uppercase tracking-widest">{date}</div>
            {sessions.map(s => (
              <div
                key={s.id}
                className={`group flex items-center rounded-md mb-0.5 ${
                  activeId === s.id ? 'bg-accent/10' : 'hover:bg-surface-3'
                }`}
              >
                <button
                  onClick={() => onSelect(s.id)}
                  className={`flex-1 text-left px-3 py-2 text-sm truncate transition-colors ${
                    activeId === s.id ? 'text-accent' : 'text-stone-500 group-hover:text-stone-300'
                  }`}
                >
                  {s.query}
                </button>
                <button
                  onClick={() => onDelete(s.id)}
                  className="opacity-0 group-hover:opacity-100 pr-2 text-stone-700 hover:text-red-500 transition-all text-xs flex-shrink-0"
                  title="Delete"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        ))}
        {history.length === 0 && (
          <p className="text-xs text-stone-700 px-2 mt-4">No research yet</p>
        )}
        {history.length > 0 && filtered.length === 0 && (
          <p className="text-xs text-stone-700 px-2 mt-4">No matches</p>
        )}
      </div>
    </div>
  )
}
