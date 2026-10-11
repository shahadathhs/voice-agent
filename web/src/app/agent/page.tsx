"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AgentClient, PcmPlayer, type TurnMetrics } from "@/lib/agent-client";
import { MicRecorder } from "@/lib/recorder";

type Phase = "idle" | "starting" | "listening" | "thinking" | "speaking";

interface Message {
  id: number;
  role: "user" | "agent";
  text: string;
  done: boolean;
  interrupted?: boolean;
}

interface Persona {
  id: string;
  label: string;
}

const PERSONAS: Persona[] = [
  { id: "assistant", label: "Assistant" },
  { id: "interviewer", label: "Interviewer" },
  { id: "storyteller", label: "Storyteller" },
];

const PHASE_LABEL: Record<Phase, string> = {
  idle: "off",
  starting: "starting…",
  listening: "● listening",
  thinking: "◆ thinking",
  speaking: "▲ speaking",
};

function phaseColor(phase: Phase): string {
  switch (phase) {
    case "listening":
      return "text-emerald-400";
    case "thinking":
      return "text-amber-400";
    case "speaking":
      return "text-sky-400";
    default:
      return "text-zinc-500";
  }
}

export default function AgentPage() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [persona, setPersona] = useState("assistant");
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<TurnMetrics[]>([]);
  const [bargeIns, setBargeIns] = useState(0);

  const clientRef = useRef<AgentClient | null>(null);
  const recorderRef = useRef<MicRecorder | null>(null);
  const playerRef = useRef<PcmPlayer | null>(null);
  const levelRef = useRef(0);
  const meterRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const agentTextRef = useRef("");
  const nextIdRef = useRef(1);
  const phaseRef = useRef<Phase>("idle");

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  useEffect(() => {
    if (phase !== "speaking" && phase !== "listening") return;
    let raf: number;
    const tick = () => {
      if (meterRef.current) {
        meterRef.current.style.width = `${Math.min(100, levelRef.current * 500)}%`;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  const stop = useCallback(async () => {
    recorderRef.current?.stop();
    recorderRef.current = null;
    await playerRef.current?.close();
    playerRef.current = null;
    clientRef.current?.close();
    clientRef.current = null;
    setPhase("idle");
    setMessages((prev) => prev.map((m) => (m.done ? m : { ...m, done: true })));
  }, []);

  useEffect(() => {
    return () => {
      recorderRef.current?.stop();
      playerRef.current?.close();
      clientRef.current?.close();
    };
  }, []);

  const start = useCallback(() => {
    setError(null);
    setPhase("starting");
    agentTextRef.current = "";
    nextIdRef.current = 1;

    const player = new PcmPlayer();
    playerRef.current = player;
    const recorder = new MicRecorder();
    recorderRef.current = recorder;

    const pushMessage = (role: "user" | "agent", text: string, done = false): number => {
      const id = nextIdRef.current++;
      setMessages((prev) => [...prev, { id, role, text, done }]);
      return id;
    };

    const client = new AgentClient({
      onReady: () => {
        player.start();
        recorder.onChunk = (pcm, level) => {
          levelRef.current = level;
          client.sendAudio(pcm);
        };
        recorder
          .start()
          .then(() => setPhase("listening"))
          .catch((err: unknown) => {
            setError(err instanceof Error ? err.message : "Microphone access denied");
            void stop();
          });
      },
      onModelLoading: () => setPhase("starting"),
      onSpeechStart: () => {
        if (phaseRef.current === "speaking" || phaseRef.current === "thinking") return;
        setPhase("listening");
      },
      onThinking: () => setPhase("thinking"),
      onSpeaking: () => setPhase("speaking"),
      onTranscript: (text) => {
        if (!text) return;
        pushMessage("user", text, true);
      },
      onLlmDelta: (text) => {
        agentTextRef.current += text;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === "agent" && !last.done) {
            return [...prev.slice(0, -1), { ...last, text: agentTextRef.current }];
          }
          const id = nextIdRef.current++;
          return [...prev, { id, role: "agent", text: agentTextRef.current, done: false }];
        });
      },
      onTurnDone: (m) => {
        agentTextRef.current = "";
        setPhase("listening");
        setMetrics((prev) => [m, ...prev].slice(0, 20));
        setMessages((prev) => prev.map((msg) => (msg.done ? msg : { ...msg, done: true })));
      },
      onInterrupted: () => {
        player.stopAll();
        agentTextRef.current = "";
        setBargeIns((n) => n + 1);
        setPhase("listening");
        setMessages((prev) => prev.map((msg) => (msg.done ? msg : { ...msg, done: true, interrupted: true })));
      },
      onError: (reason) => {
        setError(
          reason.includes("GROQ_API_KEY")
            ? "LLM not configured: set GROQ_API_KEY in backend/.env"
            : reason,
        );
      },
      onClose: () => {
        if (phaseRef.current !== "idle") {
          setPhase("idle");
        }
      },
    });

    clientRef.current = client;
    client.connect(persona, () => {});
  }, [persona, stop]);

  const running = phase !== "idle";
  const avg = (fn: (m: TurnMetrics) => number | null) => {
    const values = metrics.map(fn).filter((v): v is number => v !== null);
    return values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : null;
  };

  return (
    <main className="max-w-3xl mx-auto px-6 py-12">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-semibold">Live agent</h1>
        <Link href="/" className="text-sm text-zinc-400 hover:text-zinc-100">
          ← home
        </Link>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          {!running ? (
            <button
              onClick={start}
              className="rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-medium px-6 py-3 transition-colors"
            >
              ● Start conversation
            </button>
          ) : (
            <button
              onClick={stop}
              className="rounded-lg bg-red-500 hover:bg-red-400 text-zinc-950 font-medium px-6 py-3 transition-colors"
            >
              ■ End conversation
            </button>
          )}

          <select
            value={persona}
            onChange={(e) => setPersona(e.target.value)}
            disabled={running}
            className="rounded-lg bg-zinc-950 border border-zinc-800 px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500 disabled:opacity-50"
          >
            {PERSONAS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>

          <div className="h-2 flex-1 min-w-24 rounded-full bg-zinc-950 overflow-hidden">
            <div ref={meterRef} className="h-full w-0 rounded-full bg-emerald-400" />
          </div>

          <span className={`font-mono text-sm ${phaseColor(phase)}`}>{PHASE_LABEL[phase]}</span>
        </div>

        {error && (
          <p className="mt-4 text-sm text-red-400 rounded-lg bg-red-950/50 border border-red-900 px-4 py-2.5">
            {error}
          </p>
        )}
      </div>

      <div
        ref={scrollRef}
        className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5 h-[420px] overflow-y-auto mb-6 space-y-3"
      >
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-zinc-600 text-sm text-center px-8">
            Just talk. The agent listens for natural pauses, answers out loud, and you can
            interrupt it mid-sentence.
          </div>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                  m.role === "user"
                    ? "bg-emerald-950 border border-emerald-900 text-emerald-100"
                    : "bg-zinc-900 border border-zinc-800 text-zinc-100"
                }`}
              >
                {m.text || "…"}
                {m.interrupted && (
                  <span className="block text-xs text-amber-500 mt-1">interrupted</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="STT"
          value={avg((m) => m.sttMs)}
          unit="ms"
          hint="transcription time"
        />
        <StatCard
          label="LLM 1st token"
          value={avg((m) => m.llmFirstTokenMs)}
          unit="ms"
          hint="incl. STT time"
        />
        <StatCard
          label="Turn total"
          value={avg((m) => m.totalMs)}
          unit="ms"
          hint="speech end → reply done"
        />
        <StatCard label="Barge-ins" value={bargeIns || null} unit="" hint="interruptions" />
      </div>
    </main>
  );
}

function StatCard({
  label,
  value,
  unit,
  hint,
}: {
  label: string;
  value: number | null;
  unit: string;
  hint: string;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3">
      <div className="text-xs text-zinc-500 font-mono">{label}</div>
      <div className="text-xl font-semibold mt-1">
        {value !== null ? value : "—"}
        {value !== null && <span className="text-sm text-zinc-500 ml-1">{unit}</span>}
      </div>
      <div className="text-[11px] text-zinc-600 mt-0.5">{hint}</div>
    </div>
  );
}
