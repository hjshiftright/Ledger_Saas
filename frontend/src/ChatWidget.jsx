import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Sparkles, X, Send, Minimize2, Bot, RefreshCw, Settings } from 'lucide-react'
import { API } from './api.js'

// ── Typing indicator ──────────────────────────────────────────────────────────
function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0ms' }} />
      <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} />
      <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  )
}

// ── Basic markdown renderer for bot messages ──────────────────────────────────
function MarkdownText({ content }) {
  // Split into paragraphs on double newlines
  const paragraphs = content.split(/\n\n+/)
  return (
    <div className="space-y-1.5">
      {paragraphs.map((para, pi) => {
        // Check if this paragraph is a bullet point block
        const lines = para.split('\n')
        const isBulletBlock = lines.every(l => l.trim().startsWith('- ') || l.trim().startsWith('* ') || l.trim() === '')
        if (isBulletBlock && lines.some(l => l.trim().startsWith('- ') || l.trim().startsWith('* '))) {
          return (
            <ul key={pi} className="space-y-0.5 pl-3">
              {lines.filter(l => l.trim()).map((l, li) => (
                <li key={li} className="flex items-start gap-1.5">
                  <span className="shrink-0 mt-1 w-1 h-1 rounded-full bg-current opacity-60" />
                  <span>{formatInline(l.replace(/^[\-\*]\s*/, ''))}</span>
                </li>
              ))}
            </ul>
          )
        }
        // Regular paragraph — lines joined with <br>
        return (
          <p key={pi}>
            {lines.map((line, li) => (
              <span key={li}>
                {formatInline(line)}
                {li < lines.length - 1 && <br />}
              </span>
            ))}
          </p>
        )
      })}
    </div>
  )
}

// Simple inline formatter: **bold**
function formatInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>
    }
    return part
  })
}

// ── Single message bubble ─────────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-2`}>
      {!isUser && (
        <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 mr-2 mt-0.5">
          <Sparkles className="w-3 h-3 text-indigo-600" />
        </div>
      )}
      <div
        className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-white border border-slate-100 text-slate-700 shadow-sm rounded-bl-sm'
        }`}
      >
        {isUser ? msg.content : <MarkdownText content={msg.content} />}
      </div>
    </div>
  )
}

// ── Suggested starter questions ───────────────────────────────────────────────
const STARTERS = [
  "What's my net worth right now?",
  "How much did I spend this month?",
  "Am I on track with my goals?",
  "How long until I can retire?",
  "Which budget am I closest to hitting?",
]

// ── Main widget ───────────────────────────────────────────────────────────────
export default function ChatWidget({ onNavigate }) {
  const [open, setOpen]               = useState(false)
  const [messages, setMessages]       = useState([])   // [{role, content}]
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)
  const [hasProvider, setHasProvider] = useState(null) // null = unknown, true/false
  const bottomRef                     = useRef(null)
  const inputRef                      = useRef(null)

  // Check LLM provider whenever widget opens
  useEffect(() => {
    if (!open) return
    API.llm.list()
      .then(providers => setHasProvider(providers.some(p => p.is_active)))
      .catch(() => setHasProvider(false))
  }, [open])

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Focus input when widget opens (only when provider is ready)
  useEffect(() => {
    if (open && hasProvider) {
      setTimeout(() => inputRef.current?.focus(), 80)
    }
  }, [open, hasProvider])

  const sendMessage = useCallback(async (text) => {
    const content = (text || input).trim()
    if (!content || loading) return

    const userMsg = { role: 'user', content }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)
    setError(null)

    try {
      // Build history (exclude the message we just appended)
      const history = messages.map(m => ({ role: m.role, content: m.content }))
      const res = await API.chat.send(content, history)
      setMessages([...nextMessages, { role: 'assistant', content: res.reply }])
    } catch (err) {
      setError('Something went wrong. Try again.')
      // Remove optimistic user message on error
      setMessages(messages)
    } finally {
      setLoading(false)
    }
  }, [input, loading, messages])

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    setError(null)
    setInput('')
  }

  const isEmpty = messages.length === 0

  return (
    <>
      {/* ── Expanded panel ─────────────────────────────────────────────────── */}
      {open && (
        <div
          className="fixed bottom-20 right-5 z-50 w-[370px] bg-white rounded-2xl shadow-2xl border border-slate-100 flex flex-col overflow-hidden"
          style={{ maxHeight: '540px' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-slate-100 shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
                <Sparkles className="w-3.5 h-3.5 text-white" />
              </div>
              <div>
                <div className="text-sm font-bold text-slate-800 leading-tight">Finny</div>
                <div className="text-xs text-slate-400 leading-tight">Ask anything about your money</div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {!isEmpty && (
                <button
                  onClick={clearChat}
                  title="Clear conversation"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto p-4 bg-slate-50" style={{ minHeight: 0 }}>
            {!hasProvider ? (
              /* No LLM configured */
              <div className="flex flex-col items-center text-center pt-6 pb-2">
                <div className="w-12 h-12 rounded-2xl bg-amber-100 flex items-center justify-center mb-3">
                  <Settings className="w-6 h-6 text-amber-600" />
                </div>
                <p className="text-sm font-semibold text-slate-700 mb-1">No AI provider set up yet</p>
                <p className="text-xs text-slate-400 mb-5 leading-relaxed px-2">
                  Add a Gemini, OpenAI, or Anthropic API key in Settings and Finny will be ready to answer any question about your money.
                </p>
                <button
                  onClick={() => { setOpen(false); onNavigate?.('settings') }}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors"
                >
                  <Settings className="w-3.5 h-3.5" />
                  Go to Settings
                </button>
              </div>
            ) : isEmpty ? (
              /* Welcome state */
              <div className="flex flex-col items-center text-center pt-4 pb-2">
                <div className="w-12 h-12 rounded-2xl bg-indigo-100 flex items-center justify-center mb-3">
                  <Sparkles className="w-6 h-6 text-indigo-600" />
                </div>
                <p className="text-sm font-semibold text-slate-700 mb-1">Hey! I'm Finny 👋</p>
                <p className="text-xs text-slate-400 mb-5 leading-relaxed">
                  I have your live financial data. Ask me anything about your money.
                </p>
                <div className="w-full space-y-1.5">
                  {STARTERS.map(q => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="w-full text-left px-3 py-2 bg-white rounded-xl border border-slate-100 text-xs text-slate-600 hover:border-indigo-200 hover:text-indigo-700 hover:bg-indigo-50 transition-colors shadow-sm"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Conversation */
              <>
                {messages.map((msg, i) => (
                  <MessageBubble key={i} msg={msg} />
                ))}
                {loading && (
                  <div className="flex justify-start mb-2">
                    <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 mr-2 mt-0.5">
                      <Sparkles className="w-3 h-3 text-indigo-600" />
                    </div>
                    <div className="bg-white border border-slate-100 rounded-xl rounded-bl-sm shadow-sm">
                      <TypingDots />
                    </div>
                  </div>
                )}
                {error && (
                  <div className="text-xs text-rose-500 text-center mt-1">{error}</div>
                )}
                <div ref={bottomRef} />

                {/* Suggestion chips — always visible during chat */}
                {!loading && (
                  <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
                    {STARTERS.map(q => (
                      <button
                        key={q}
                        onClick={() => sendMessage(q)}
                        className="shrink-0 px-2.5 py-1 bg-white border border-slate-200 rounded-full text-xs text-slate-600 hover:border-indigo-300 hover:text-indigo-700 hover:bg-indigo-50 transition-colors shadow-sm whitespace-nowrap"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Input bar — hidden when no provider */}
          {hasProvider && (
          <div className="px-3 py-3 bg-white border-t border-slate-100 shrink-0">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about your net worth, goals, spending…"
                rows={2}
                disabled={loading}
                className="flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-200 disabled:opacity-50 leading-relaxed overflow-hidden"
                style={{ minHeight: 64, maxHeight: 140 }}
                onInput={e => {
                  e.target.style.height = 'auto'
                  const next = e.target.scrollHeight
                  e.target.style.height = next + 'px'
                  e.target.style.overflowY = next >= 140 ? 'auto' : 'hidden'
                }}
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || loading}
                className="w-8 h-8 shrink-0 rounded-xl bg-indigo-600 flex items-center justify-center text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
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

      {/* ── Collapsed trigger button ────────────────────────────────────────── */}
      <button
        onClick={() => setOpen(o => !o)}
        className={`fixed bottom-5 right-5 z-50 flex items-center gap-2 px-4 py-3 rounded-2xl shadow-lg transition-all duration-200
          ${open
            ? 'bg-slate-700 text-white hover:bg-slate-800'
            : 'bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-xl hover:scale-105'
          }`}
      >
        {open ? (
          <Minimize2 className="w-4 h-4" />
        ) : (
          <Sparkles className="w-4 h-4" />
        )}
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
