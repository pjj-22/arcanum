import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import AgentFeed from './components/AgentFeed'
import SettingsModal from './components/SettingsModal'
import Sidebar from './components/Sidebar'
import SourceList from './components/SourceList'

function QueryInput({ onSubmit, autoFocus }) {
  const [value, setValue] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    if (autoFocus) ref.current?.focus()
  }, [autoFocus])

  const submit = () => {
    const q = value.trim()
    if (!q) return
    onSubmit(q)
    setValue('')
  }

  return (
    <div className="flex gap-3 items-end">
      <textarea
        ref={ref}
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            submit()
          }
        }}
        placeholder="What do you want to research?"
        rows={1}
        className="flex-1 bg-surface-2 border border-surface-3 focus:border-accent rounded-xl px-4 py-3 text-sm text-stone-300 placeholder-stone-700 resize-none focus:outline-none transition-colors"
        style={{ maxHeight: '140px' }}
      />
      <button
        onClick={submit}
        disabled={!value.trim()}
        className="px-5 py-3 bg-accent hover:bg-accent-dim disabled:opacity-40 text-white rounded-xl text-sm font-medium transition-colors flex-shrink-0"
      >
        Research
      </button>
    </div>
  )
}

function ResearchView({ query, events, streamText, answer, sources, loading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamText, answer])

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 overflow-y-auto px-8 py-6 min-w-0">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-xl font-semibold text-stone-200 mb-6">{query}</h1>
          <AgentFeed events={events} />
          {(streamText || answer) && (
            <div className="prose max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {answer || streamText}
              </ReactMarkdown>
              {loading && (
                <span className="inline-block w-1.5 h-4 bg-accent ml-0.5 animate-pulse rounded-sm" />
              )}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {sources && sources.length > 0 && (
        <div className="w-72 flex-shrink-0 border-l border-surface-3 overflow-y-auto px-4 py-6">
          <SourceList sources={sources} query={query} answer={answer} />
        </div>
      )}
    </div>
  )
}

function LoadingView({ query, events, streamText }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamText])

  return (
    <div className="flex-1 overflow-y-auto px-8 py-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-xl font-semibold text-stone-200 mb-6">{query}</h1>
        <AgentFeed events={events} />
        {streamText && (
          <div className="prose max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamText}</ReactMarkdown>
            <span className="inline-block w-1.5 h-4 bg-accent ml-0.5 animate-pulse rounded-sm" />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function EmptyState({ onSubmit }) {
  return (
    <div className="flex-1 flex items-center justify-center px-8">
      <div className="w-full max-w-xl">
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-accent text-xl font-semibold">A</span>
          </div>
          <h2 className="text-stone-300 font-semibold text-lg mb-1">Arcanum</h2>
          <p className="text-sm text-stone-600">Research anything across the web and your personal notes.</p>
        </div>
        <QueryInput onSubmit={onSubmit} autoFocus />
        <p className="text-xs text-stone-700 mt-3 text-center">Enter to submit · Shift+Enter for newline</p>
      </div>
    </div>
  )
}

export default function App() {
  const [activeSession, setActiveSession] = useState(null)
  const [query, setQuery] = useState('')
  const [events, setEvents] = useState([])
  const [streamText, setStreamText] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const esRef = useRef(null)

  const reset = () => {
    setQuery('')
    setEvents([])
    setStreamText('')
    setAnswer('')
    setSources([])
    setActiveSession(null)
    setLoading(false)
  }

  const loadSession = async (id) => {
    const r = await fetch(`/api/history/${id}`)
    const s = await r.json()
    setActiveSession(id)
    setQuery(s.query)
    setAnswer(s.answer || '')
    setSources(s.sources || [])
    setEvents([])
    setStreamText('')
    setLoading(false)
  }

  const startResearch = useCallback((q) => {
    if (esRef.current) esRef.current.abort()
    setQuery(q)
    setEvents([])
    setStreamText('')
    setAnswer('')
    setSources([])
    setActiveSession(null)
    setLoading(true)

    const ctrl = new AbortController()
    esRef.current = ctrl

    fetch('/api/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q }),
      signal: ctrl.signal,
    }).then(async res => {
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentStream = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try {
            const evt = JSON.parse(raw)
            console.log('[arcanum]', evt.type, evt)
            if (evt.type === 'agent') {
              setEvents(prev => {
                const existing = prev.findIndex(e => e.name === evt.name && e.status === 'running')
                if (existing >= 0 && evt.status !== 'running') {
                  const next = [...prev]
                  next[existing] = evt
                  return next
                }
                return [...prev, evt]
              })
            } else if (evt.type === 'stream_chunk') {
              currentStream += evt.text
              setStreamText(currentStream)
            } else if (evt.type === 'stream_end') {
              setAnswer(currentStream)
              setStreamText('')
            } else if (evt.type === 'complete') {
              setSources(evt.sources || [])
              setLoading(false)
            } else if (evt.type === 'session') {
              setActiveSession(evt.id)
            } else if (evt.type === 'error') {
              setLoading(false)
            }
          } catch {}
        }
      }
      setLoading(false)
    }).catch(err => {
      if (err.name !== 'AbortError') setLoading(false)
    })
  }, [])

  return (
    <div className="flex h-screen bg-surface-0 overflow-hidden">
      <Sidebar activeId={activeSession} onSelect={loadSession} onNew={reset} onDeleted={reset} />

      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center justify-end px-6 py-3 border-b border-surface-3 flex-shrink-0">
          <button
            onClick={() => setShowSettings(true)}
            className="text-xs text-stone-600 hover:text-stone-500 transition-colors flex items-center gap-1.5"
          >
            <span>⚙</span> Settings
          </button>
        </div>

        {!query && <EmptyState onSubmit={startResearch} />}
        {query && loading && <LoadingView query={query} events={events} streamText={streamText} />}
        {query && !loading && (
          <ResearchView
            query={query}
            events={events}
            streamText={streamText}
            answer={answer}
            sources={sources}
            loading={false}
          />
        )}
      </div>

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  )
}
