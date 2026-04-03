import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'
import { Sparkles, Send, RefreshCw, Minimize2, Settings, X } from 'lucide-react'
import { API } from './api.js'

// ── Brand colour ──────────────────────────────────────────────────────────────
const NAVY = '#2C4A70'
const NAVY_DARK = '#1F344F'

// ── Markdown renderer ─────────────────────────────────────────────────────────
function MarkdownText({ content }) {
  const paragraphs = content.split(/\n\n+/)
  return (
    <div className="space-y-1.5">
      {paragraphs.map((para, pi) => {
        const lines = para.split('\n')
        const isBulletBlock = lines.every(l => l.trim().startsWith('- ') || l.trim().startsWith('* ') || l.trim() === '')
        if (isBulletBlock && lines.some(l => l.trim().startsWith('- ') || l.trim().startsWith('* '))) {
          return (
            <ul key={pi} className="space-y-0.5 pl-3">
              {lines.filter(l => l.trim()).map((l, li) => (
                <li key={li} className="flex items-start gap-1.5">
                  <span className="shrink-0 mt-1.5 w-1 h-1 rounded-full bg-current opacity-50" />
                  <span>{inlineFormat(l.replace(/^[\-\*]\s*/, ''))}</span>
                </li>
              ))}
            </ul>
          )
        }
        return (
          <p key={pi}>
            {lines.map((line, li) => (
              <span key={li}>
                {inlineFormat(line)}
                {li < lines.length - 1 && <br />}
              </span>
            ))}
          </p>
        )
      })}
    </div>
  )
}

function inlineFormat(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i} className="font-semibold">{p.slice(2, -2)}</strong>
      : p
  )
}

// ── Message bubble ────────────────────────────────────────────────────────────
function Bubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-2`}>
      {!isUser && (
        <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mr-2 mt-0.5"
          style={{ background: NAVY }}>
          <Sparkles className="w-3 h-3 text-white" />
        </div>
      )}
      <div
        className={`max-w-[80%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'text-white rounded-tr-sm'
            : 'bg-white border border-slate-100 text-slate-700 shadow-sm rounded-tl-sm'
        }`}
        style={isUser ? { background: NAVY } : {}}
      >
        {isUser ? msg.content : <MarkdownText content={msg.content} />}
      </div>
    </div>
  )
}

// ── Typing indicator ──────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex justify-start mb-2">
      <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mr-2 mt-0.5"
        style={{ background: NAVY }}>
        <Sparkles className="w-3 h-3 text-white" />
      </div>
      <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm shadow-sm px-4 py-3 flex gap-1 items-center">
        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// INLINE MODE — fills its container, used as a sidebar panel
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * FinnyInline — self-contained inline chat panel.
 *
 * Props:
 *   subtitle         – line below "Finny" in the header
 *   placeholder      – textarea placeholder
 *   prompts          – array of quick-prompt strings
 *   showPromptsAlways– keep prompt chips visible even after messages exist
 *   initialMessage   – first message Finny sends on mount
 *   onSend(text)     – async fn; return a string → auto-appended as Finny reply
 *                      return null/undefined → caller injects via ref
 *
 * Ref exposes: { addMessage({ role: 'finny'|'user', content }) }
 */
export const FinnyInline = forwardRef(function FinnyInline(
  {
    subtitle = 'Your financial companion',
    placeholder = 'Ask Finny anything…',
    prompts = [],
    showPromptsAlways = false,
    initialMessage,
    onSend,
  },
  ref
) {
  const [messages, setMessages] = useState(() =>
    initialMessage ? [{ role: 'finny', content: initialMessage }] : []
  )
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const inputRef  = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const addMessage = (msg) => setMessages(m => [...m, msg])

  useImperativeHandle(ref, () => ({ addMessage }))

  const send = async (text) => {
    const content = (text ?? input).trim()
    if (!content || thinking) return
    setInput('')
    addMessage({ role: 'user', content })
    setThinking(true)
    try {
      const reply = await onSend?.(content)
      if (reply != null) addMessage({ role: 'finny', content: reply })
    } finally {
      setThinking(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  const hasMessages   = messages.length > 1
  const showPrompts   = prompts.length > 0 && (showPromptsAlways || !hasMessages)

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 shrink-0 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center shadow-md"
          style={{ background: NAVY }}>
          <Sparkles size={16} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-black leading-tight" style={{ color: NAVY }}>Finny</p>
          <p className="text-[11px] text-slate-400 leading-tight">{subtitle}</p>
        </div>
        <span className="ml-auto w-2 h-2 rounded-full bg-emerald-400 animate-pulse"
          style={{ boxShadow: '0 0 6px rgba(52,211,153,0.7)' }} />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 bg-slate-50" style={{ minHeight: 0 }}>
        {messages.map((m, i) => <Bubble key={i} msg={m} />)}
        {thinking && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      {showPrompts && (
        <div className="px-4 py-2.5 flex flex-wrap gap-1.5 border-t border-slate-100 bg-white shrink-0">
          {prompts.map((p, i) => (
            <button
              key={i}
              onClick={() => send(p)}
              className="text-[11px] font-semibold px-3 py-1.5 rounded-full transition-colors border whitespace-nowrap hover:opacity-80"
              style={{
                background: `${NAVY}14`,
                color: NAVY,
                borderColor: `${NAVY}30`,
              }}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-4 pb-4 pt-2.5 bg-white border-t border-slate-100 shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder={placeholder}
            rows={2}
            disabled={thinking}
            className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none disabled:opacity-50 transition-colors"
            onFocus={e => { e.target.style.borderColor = NAVY; e.target.style.boxShadow = `0 0 0 3px ${NAVY}18` }}
            onBlur={e => { e.target.style.borderColor = ''; e.target.style.boxShadow = '' }}
            style={{ minHeight: 64, maxHeight: 120 }}
            onInput={e => {
              e.target.style.height = 'auto'
              const h = e.target.scrollHeight
              e.target.style.height = h + 'px'
              e.target.style.overflowY = h >= 120 ? 'auto' : 'hidden'
            }}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || thinking}
            className="w-9 h-9 shrink-0 rounded-xl flex items-center justify-center text-white transition-opacity disabled:opacity-40"
            style={{ background: NAVY }}
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  )
})

// ═══════════════════════════════════════════════════════════════════════════════
// FLOATING MODE — fixed bottom-right button + panel (used in main app shell)
// ═══════════════════════════════════════════════════════════════════════════════

const FLOATING_PROMPTS = [
  "What's my net worth right now?",
  "How much did I spend this month?",
  "Am I on track with my goals?",
  "How long until I can retire?",
  "Which budget am I closest to hitting?",
]

export function FinnyFloating({ onNavigate }) {
  const [open, setOpen]               = useState(false)
  const [messages, setMessages]       = useState([])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)
  const [hasProvider, setHasProvider] = useState(null)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  useEffect(() => {
    if (!open) return
    API.llm.list()
      .then(providers => setHasProvider(providers.some(p => p.is_active)))
      .catch(() => setHasProvider(false))
  }, [open])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (open && hasProvider) setTimeout(() => inputRef.current?.focus(), 80)
  }, [open, hasProvider])

  const addMessage = (msg) => setMessages(m => [...m, msg])

  const send = async (text) => {
    const content = (text ?? input).trim()
    if (!content || loading) return
    const userMsg = { role: 'user', content }
    const next = [...messages, userMsg]
    setMessages(next)
    setInput('')
    setLoading(true)
    setError(null)
    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }))
      const res = await API.chat.send(content, history)
      addMessage({ role: 'finny', content: res.reply })
    } catch {
      setError('Something went wrong. Try again.')
      setMessages(messages)
    } finally {
      setLoading(false)
    }
  }

  const clearChat = () => { setMessages([]); setError(null); setInput('') }
  const isEmpty = messages.length === 0

  return (
    <>
      {/* Panel */}
      {open && (
        <div
          className="fixed bottom-20 right-5 z-50 bg-white rounded-2xl shadow-2xl border border-slate-100 flex flex-col overflow-hidden"
          style={{ width: 370, maxHeight: 540 }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center"
                style={{ background: NAVY }}>
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="text-sm font-black leading-tight" style={{ color: NAVY }}>Finny</div>
                <div className="text-xs text-slate-400 leading-tight">Ask anything about your money</div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {!isEmpty && (
                <button onClick={clearChat} title="Clear conversation"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors">
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              )}
              <button onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-4 bg-slate-50" style={{ minHeight: 0 }}>
            {!hasProvider ? (
              <div className="flex flex-col items-center text-center pt-6 pb-2">
                <div className="w-12 h-12 rounded-2xl bg-amber-100 flex items-center justify-center mb-3">
                  <Settings className="w-6 h-6 text-amber-600" />
                </div>
                <p className="text-sm font-semibold text-slate-700 mb-1">No AI provider set up yet</p>
                <p className="text-xs text-slate-400 mb-5 leading-relaxed px-2">
                  Add a Gemini, OpenAI, or Anthropic API key in Settings and Finny will be ready to help.
                </p>
                <button
                  onClick={() => { setOpen(false); onNavigate?.('settings') }}
                  className="flex items-center gap-2 px-4 py-2 text-white text-sm font-semibold rounded-xl transition-colors"
                  style={{ background: NAVY }}
                >
                  <Settings className="w-3.5 h-3.5" />
                  Go to Settings
                </button>
              </div>
            ) : isEmpty ? (
              <div className="flex flex-col items-center text-center pt-4 pb-2">
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3"
                  style={{ background: `${NAVY}18` }}>
                  <Sparkles className="w-6 h-6" style={{ color: NAVY }} />
                </div>
                <p className="text-sm font-semibold text-slate-700 mb-1">Hey! I'm Finny 👋</p>
                <p className="text-xs text-slate-400 mb-5 leading-relaxed">
                  I have your live financial data. Ask me anything about your money.
                </p>
                <div className="w-full space-y-1.5">
                  {FLOATING_PROMPTS.map(q => (
                    <button key={q} onClick={() => send(q)}
                      className="w-full text-left px-3 py-2 bg-white rounded-xl border border-slate-100 text-xs text-slate-600 hover:border-opacity-50 hover:bg-opacity-5 transition-colors shadow-sm"
                      style={{ '--hover-border': NAVY }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = `${NAVY}50`; e.currentTarget.style.color = NAVY }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = ''; e.currentTarget.style.color = '' }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => <Bubble key={i} msg={msg} />)}
                {loading && <TypingIndicator />}
                {error && <div className="text-xs text-rose-500 text-center mt-1">{error}</div>}
                <div ref={bottomRef} />
                {!loading && (
                  <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1">
                    {FLOATING_PROMPTS.map(q => (
                      <button key={q} onClick={() => send(q)}
                        className="shrink-0 px-2.5 py-1 bg-white border border-slate-200 rounded-full text-xs text-slate-600 transition-colors shadow-sm whitespace-nowrap"
                        onMouseEnter={e => { e.currentTarget.style.borderColor = `${NAVY}50`; e.currentTarget.style.color = NAVY }}
                        onMouseLeave={e => { e.currentTarget.style.borderColor = ''; e.currentTarget.style.color = '' }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Input */}
          {hasProvider && (
            <div className="px-3 py-3 bg-white border-t border-slate-100 shrink-0">
              <div className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
                  placeholder="Ask about your net worth, goals, spending…"
                  rows={2}
                  disabled={loading}
                  className="flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none disabled:opacity-50 leading-relaxed overflow-hidden bg-slate-50"
                  style={{ minHeight: 64, maxHeight: 140 }}
                  onFocus={e => { e.target.style.borderColor = NAVY; e.target.style.boxShadow = `0 0 0 3px ${NAVY}18` }}
                  onBlur={e => { e.target.style.borderColor = ''; e.target.style.boxShadow = '' }}
                  onInput={e => {
                    e.target.style.height = 'auto'
                    const h = e.target.scrollHeight
                    e.target.style.height = h + 'px'
                    e.target.style.overflowY = h >= 140 ? 'auto' : 'hidden'
                  }}
                />
                <button
                  onClick={() => send()}
                  disabled={!input.trim() || loading}
                  className="w-8 h-8 shrink-0 rounded-xl flex items-center justify-center text-white disabled:opacity-40 transition-opacity"
                  style={{ background: NAVY }}
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
              <p className="text-xs text-slate-300 mt-1.5 text-center">
                Answers are based on your live data · Enter to send
              </p>
            </div>
          )}
        </div>
      )}

      {/* Trigger button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-5 right-5 z-50 flex items-center gap-2 px-4 py-3 rounded-2xl shadow-lg transition-all duration-200 text-white"
        style={{
          background: open ? '#334155' : NAVY,
        }}
        onMouseEnter={e => { if (!open) e.currentTarget.style.background = NAVY_DARK }}
        onMouseLeave={e => { e.currentTarget.style.background = open ? '#334155' : NAVY }}
      >
        {open ? <Minimize2 className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
        <span className="text-sm font-semibold leading-none">
          {open ? 'Minimise' : 'Ask Finny'}
        </span>
        {!open && messages.length > 0 && (
          <span className="w-2 h-2 rounded-full bg-emerald-400 absolute -top-0.5 -right-0.5" />
        )}
      </button>
    </>
  )
}

// Default export = floating widget (drop-in replacement for ChatWidget)
export default FinnyFloating
