"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ECHO_WS_URL, MicRecorder, STT_WS_URL } from "@/lib/recorder";

type Status = "disconnected" | "connecting" | "connected";
type MicState = "idle" | "connecting" | "listening" | "error";

interface LogEntry {
  time: string;
  message: string;
  kind: "info" | "success" | "error";
}

interface Transcript {
  text: string;
  sttMs: number;
  audioMs: number;
}

function now(): string {
  return new Date().toLocaleTimeString();
}

export default function PlayPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-16">
      <div className="flex items-center justify-between mb-10">
        <h1 className="text-3xl font-semibold">Playground</h1>
        <Link href="/" className="text-sm text-zinc-400 hover:text-zinc-100">
          ← back
        </Link>
      </div>
      <SocketTest />
      <MicTranscription />
    </main>
  );
}

function SocketTest() {
  const [status, setStatus] = useState<Status>("disconnected");
  const [log, setLog] = useState<LogEntry[]>([]);
  const [pingMs, setPingMs] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const addLog = useCallback((message: string, kind: LogEntry["kind"] = "info") => {
    setLog((prev) => [{ time: now(), message, kind }, ...prev].slice(0, 30));
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) return;
    setStatus("connecting");
    const ws = new WebSocket(ECHO_WS_URL);
    ws.binaryType = "arraybuffer";
    ws.onopen = () => setStatus("connected");
    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const msg = JSON.parse(event.data);
        if (msg.type === "ready") addLog(`echo socket ready (stage: ${msg.stage})`, "success");
        if (msg.type === "pong") addLog("pong", "success");
      }
    };
    ws.onerror = () => addLog("WebSocket error", "error");
    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
    };
    wsRef.current = ws;
  }, [addLog]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const sendPing = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const start = performance.now();
    ws.send(JSON.stringify({ type: "ping" }));
    const onMessage = (event: MessageEvent) => {
      if (typeof event.data === "string" && JSON.parse(event.data).type === "pong") {
        setPingMs(Math.round(performance.now() - start));
        ws.removeEventListener("message", onMessage);
      }
    };
    ws.addEventListener("message", onMessage);
  }, []);

  const sendEchoChunk = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const chunk = crypto.getRandomValues(new Uint8Array(4096));
    const start = performance.now();
    ws.send(chunk.buffer);
    const onMessage = (event: MessageEvent) => {
      if (event.data instanceof ArrayBuffer) {
        const ok = event.data.byteLength === chunk.length;
        addLog(
          `echo ${event.data.byteLength}B in ${Math.round(performance.now() - start)}ms ${ok ? "✓" : "✗"}`,
          ok ? "success" : "error",
        );
        ws.removeEventListener("message", onMessage);
      }
    };
    ws.addEventListener("message", onMessage);
  }, [addLog]);

  const statusColor =
    status === "connected"
      ? "bg-emerald-500"
      : status === "connecting"
        ? "bg-amber-500"
        : "bg-zinc-600";

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold">Socket test</h2>
        <span className="flex items-center gap-2 text-sm text-zinc-400">
          <span className={`w-2.5 h-2.5 rounded-full ${statusColor}`} />
          {status}
          {pingMs !== null && <span className="font-mono text-xs">· {pingMs}ms</span>}
        </span>
      </div>
      <div className="flex gap-3 mb-4">
        {status === "disconnected" ? (
          <button
            onClick={connect}
            className="rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-medium px-5 py-2.5 text-sm transition-colors"
          >
            Connect to /ws
          </button>
        ) : (
          <button
            onClick={disconnect}
            className="rounded-lg border border-zinc-700 hover:border-zinc-500 px-5 py-2.5 text-sm transition-colors"
          >
            Disconnect
          </button>
        )}
        <button
          onClick={sendPing}
          disabled={status !== "connected"}
          className="rounded-lg border border-zinc-700 hover:border-zinc-500 disabled:opacity-40 px-5 py-2.5 text-sm transition-colors"
        >
          Ping
        </button>
        <button
          onClick={sendEchoChunk}
          disabled={status !== "connected"}
          className="rounded-lg border border-zinc-700 hover:border-zinc-500 disabled:opacity-40 px-5 py-2.5 text-sm transition-colors"
        >
          4KB echo
        </button>
      </div>
      <div className="rounded-xl bg-zinc-950 p-4 font-mono text-xs h-36 overflow-y-auto">
        {log.length === 0 ? (
          <p className="text-zinc-600">Echo events…</p>
        ) : (
          log.map((entry, i) => (
            <div key={i}>
              <span className="text-zinc-600">{entry.time}</span>{" "}
              <span
                className={
                  entry.kind === "success"
                    ? "text-emerald-400"
                    : entry.kind === "error"
                      ? "text-red-400"
                      : "text-zinc-300"
                }
              >
                {entry.message}
              </span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function MicTranscription() {
  const [micState, setMicState] = useState<MicState>("idle");
  const [modelLoading, setModelLoading] = useState(false);
  const [speechActive, setSpeechActive] = useState(false);
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MicRecorder | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const meterRef = useRef<HTMLDivElement>(null);
  const levelRef = useRef(0);
  const micStateRef = useRef<MicState>("idle");
  const wantMicRef = useRef(false);

  useEffect(() => {
    micStateRef.current = micState;
  }, [micState]);

  useEffect(() => {
    if (micState !== "listening") return;
    let raf: number;
    const tick = () => {
      if (meterRef.current) {
        meterRef.current.style.width = `${Math.min(100, levelRef.current * 500)}%`;
        meterRef.current.style.backgroundColor = levelRef.current > 0.1 ? "#f87171" : "#34d399";
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [micState]);

  useEffect(() => {
    return () => {
      recorderRef.current?.stop();
      wsRef.current?.close();
    };
  }, []);

  const stopEverything = useCallback(() => {
    wantMicRef.current = false;
    recorderRef.current?.stop();
    recorderRef.current = null;
    wsRef.current?.close();
    wsRef.current = null;
    setMicState("idle");
    setSpeechActive(false);
  }, []);

  const startMic = useCallback(() => {
    setError(null);
    setMicState("connecting");
    wantMicRef.current = true;

    const ws = new WebSocket(STT_WS_URL);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onclose = () => {
      if (wantMicRef.current && micStateRef.current !== "idle") {
        setError("Backend connection lost");
        setMicState("error");
        recorderRef.current?.stop();
        recorderRef.current = null;
        wantMicRef.current = false;
      }
    };

    ws.onmessage = (event) => {
      if (typeof event.data !== "string") return;
      const msg = JSON.parse(event.data);
      switch (msg.type) {
        case "model_status":
          setModelLoading(true);
          break;
        case "ready": {
          setModelLoading(false);
          const recorder = new MicRecorder();
          recorderRef.current = recorder;
          recorder.onChunk = (pcm, level) => {
            levelRef.current = level;
            if (ws.readyState === WebSocket.OPEN) ws.send(pcm);
          };
          recorder
            .start()
            .then(() => setMicState("listening"))
            .catch((err: unknown) => {
              setError(err instanceof Error ? err.message : "Microphone access denied");
              setMicState("error");
              ws.close();
            });
          break;
        }
        case "speech_start":
          setSpeechActive(true);
          break;
        case "transcript":
          setSpeechActive(false);
          setTranscripts((prev) =>
            [{ text: msg.text, sttMs: msg.stt_ms, audioMs: msg.audio_ms }, ...prev].slice(0, 50),
          );
          break;
      }
    };
  }, []);

  const listening = micState === "listening";

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold">Microphone → transcript</h2>
        <span className="font-mono text-xs text-zinc-500">/ws/stt</span>
      </div>

      <div className="flex items-center gap-4 mb-5">
        {!listening ? (
          <button
            onClick={startMic}
            disabled={micState === "connecting"}
            className="rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-zinc-950 font-medium px-5 py-2.5 text-sm transition-colors"
          >
            {micState === "connecting" ? "Starting…" : "● Start talking"}
          </button>
        ) : (
          <button
            onClick={stopEverything}
            className="rounded-lg bg-red-500 hover:bg-red-400 text-zinc-950 font-medium px-5 py-2.5 text-sm transition-colors"
          >
            ■ Stop
          </button>
        )}

        <div className="h-2 flex-1 rounded-full bg-zinc-950 overflow-hidden">
          <div ref={meterRef} className="h-full w-0 rounded-full bg-emerald-400" />
        </div>

        <span className="text-sm text-zinc-400 min-w-28 text-right">
          {modelLoading
            ? "loading model…"
            : speechActive
              ? "listening…"
              : listening
                ? "ready"
                : micState === "connecting"
                  ? "connecting…"
                  : micState === "error"
                    ? "error"
                    : "idle"}
        </span>
      </div>

      {error && (
        <p className="text-red-400 text-sm mb-5 rounded-lg bg-red-950/50 border border-red-900 px-4 py-2.5">
          {error}
        </p>
      )}

      <div className="space-y-2">
        {transcripts.length === 0 ? (
          <p className="text-zinc-600 text-sm">
            {listening
              ? "Say something — transcript appears after you stop speaking."
              : "Start the mic and speak; the backend detects utterances and transcribes them."}
          </p>
        ) : (
          transcripts.map((t, i) => (
            <div key={i} className="rounded-xl bg-zinc-950 border border-zinc-800 px-4 py-3">
              <p className="text-sm">{t.text}</p>
              <p className="font-mono text-xs text-zinc-500 mt-1.5">
                {t.audioMs}ms audio → {t.sttMs}ms stt ({(t.sttMs / Math.max(t.audioMs, 1)).toFixed(2)}×
                rt)
              </p>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
