import { useEffect, useState } from 'react'

export default function SettingsModal({ onClose }) {
  const [vaultPath, setVaultPath] = useState('')
  const [anthropicKey, setAnthropicKey] = useState('')
  const [status, setStatus] = useState(null)
  const [settings, setSettings] = useState(null)

  useEffect(() => {
    fetch('/api/settings')
      .then(r => r.json())
      .then(s => {
        setSettings(s)
        setVaultPath(s.vault_path || '')
      })
  }, [])

  const save = async () => {
    setStatus('saving')
    const body = { vault_path: vaultPath }
    if (anthropicKey) body.anthropic_key = anthropicKey

    const r = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (r.ok) {
      setStatus('saved')
      setTimeout(() => setStatus(null), 2000)
    } else {
      setStatus('error')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-surface-1 border border-surface-3 rounded-2xl p-6 w-full max-w-md mx-4"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-semibold text-stone-300">Settings</h2>
          <button onClick={onClose} className="text-stone-600 hover:text-stone-500 text-sm">✕</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-stone-600 block mb-1.5">Anthropic API Key</label>
            {settings?.has_anthropic_key && !anthropicKey && (
              <div className="text-xs text-emerald-500 mb-1.5">✓ Key is set</div>
            )}
            <input
              type="password"
              placeholder={settings?.has_anthropic_key ? "Enter new key to update" : "sk-ant-..."}
              value={anthropicKey}
              onChange={e => setAnthropicKey(e.target.value)}
              className="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-sm text-stone-300 placeholder-stone-700 focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="text-xs text-stone-600 block mb-1.5">Obsidian Vault Path</label>
            <input
              type="text"
              placeholder="/home/you/Obsidian/vault"
              value={vaultPath}
              onChange={e => setVaultPath(e.target.value)}
              className="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-sm font-mono text-stone-300 placeholder-stone-700 focus:outline-none focus:border-accent"
            />
            <p className="text-xs text-stone-600 mt-1">
              Full path to your Obsidian vault folder. Leave empty to skip note search.
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-stone-500 hover:text-stone-300 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={status === 'saving'}
            className="px-4 py-2 text-sm bg-accent hover:bg-accent-dim text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {status === 'saving' ? 'Saving...' : status === 'saved' ? 'Saved ✓' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
