import { useState, useRef, useEffect } from "react";
import client from "../api/client";
import { SourceTag } from "../components/Common";

const SUGGESTIONS = [
  "Why are we holding too much USD liquidity?",
  "Which corridor has the largest excess liquidity?",
  "What happens if USD_INR demand increases by 30%?",
  "What if volatility increases by 25%?",
  "Which recommendation is based on a regulatory rule?",
  "Which constraint prevents further reduction?",
];

export default function Agent() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function send(question) {
    const q = question ?? input;
    if (!q.trim() || sending) return;
    setInput("");
    setSending(true);
    setMessages((m) => [...m, { role: "user", content: q }]);
    try {
      const res = await client.post("/api/agent/ask", { question: q, session_id: sessionId });
      setSessionId(res.data.session_id);
      setMessages((m) => [...m, {
        role: "agent", content: res.data.answer, tools_used: res.data.tools_used, sources: res.data.sources,
      }]);
    } catch {
      setMessages((m) => [...m, { role: "agent", content: "Something went wrong reaching the agent tools. Try again." }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-4 flex flex-col h-[calc(100vh-6rem)]">
      <div>
        <h1 className="font-display text-2xl font-semibold">Agent</h1>
        <p className="text-sm text-muted mt-1">
          Deterministic by default; optional LLM-assisted routing available — answers are always template-composed from real data, never LLM-generated.
        </p>
      </div>

      <div className="flex-1 card p-4 overflow-y-auto scrollbar-thin space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} className="text-xs px-3 py-1.5 rounded-full border border-border text-muted hover:text-teal hover:border-teal transition-colors">
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] rounded-lg px-3.5 py-2.5 text-sm ${m.role === "user" ? "bg-teal text-bg" : "bg-raised border border-border"}`}>
              <div className="whitespace-pre-line">{m.content}</div>
              {m.sources && m.sources.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-border/60">
                  {m.sources.map((s, j) => <SourceTag key={j} type={s.source_type} />)}
                </div>
              )}
              {m.tools_used && m.tools_used.length > 0 && (
                <div className="text-[10px] text-faint font-mono mt-1.5">tools: {m.tools_used.join(", ")}</div>
              )}
            </div>
          </div>
        ))}
        {sending && <div className="text-muted text-xs">Agent is calling tools...</div>}
        <div ref={endRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about liquidity, a corridor scenario, or a regulation/practice lookup..."
          className="flex-1 bg-raised border border-border rounded-md px-3.5 py-2.5 text-sm focus:border-teal outline-none"
        />
        <button type="submit" disabled={sending} className="bg-teal text-bg font-medium text-sm rounded-md px-4 py-2.5 hover:bg-teal/90 disabled:opacity-60">
          Ask
        </button>
      </form>
    </div>
  );
}
