"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";

type Status = "disconnected" | "connecting" | "connected";

interface LogEntry {
  time: string;
  message: string;
  kind: "info" | "success" | "error";
}

function now(): string {
  return new Date().toLocaleTimeString();
}

export default function PlayPage() {
  const [url, setUrl] = useState("ws://localhost:8000/ws");
  const [status, setStatus] = useState<Status>("disconnected");
  const [log, setLog] = useState<LogEntry[]>([]);
  const [pingMs, setPingMs] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const addLog = useCallback((message: string, kind: LogEntry["kind"] = "info") => {
    setLog((prev) => [{ time: now(), message, kind }, ...prev].slice(0, 50));
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) return;
    setStatus("connecting");
    addLog(`Connecting to ${url}…`);

    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      setStatus("connected");
      addLog("Connected", "success");
    };
    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const msg = JSON.parse(event.data);
        if (msg.type === "ready") addLog(`Backend ready (stage: ${msg.stage})`, "success");
        if (msg.type === "pong") addLog("pong", "success");
      }
    };
    ws.onerror = () => addLog("WebSocket error", "error");
    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
      addLog("Disconnected");
    };

    wsRef.current = ws;
  }, [url, addLog]);

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
    <main className="max-w-3xl mx-auto px-6 py-16">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-semibold">Playground</h1>
        <Link href="/" className="text-sm text-zinc-400 hover:text-zinc-100">
          ← back
        </Link>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6 mb-6">
        <label className="block text-sm text-zinc-400 mb-2">Backend WebSocket URL</label>
        <div className="flex gap-3">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={status !== "disconnected"}
            className="flex-1 rounded-lg bg-zinc-950 border border-zinc-800 px-4 py-2.5 font-mono text-sm focus:outline-none focus:border-emerald-500 disabled:opacity-50"
          />
          {status === "disconnected" ? (
            <button
              onClick={connect}
              className="rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-medium px-5 transition-colors"
            >
              Connect
            </button>
          ) : (
            <button
              onClick={disconnect}
              className="rounded-lg border border-zinc-700 hover:border-zinc-500 px-5 transition-colors"
            >
              Disconnect
            </button>
          )}
        </div>
        <div className="flex items-center gap-6 mt-4 text-sm">
          <span className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${statusColor}`} />
            {status}
          </span>
          {pingMs !== null && <span className="text-zinc-400">ping: {pingMs}ms</span>}
        </div>
      </div>

      <div className="flex gap-3 mb-6">
        <button
          onClick={sendPing}
          disabled={status !== "connected"}
          className="rounded-lg border border-zinc-700 hover:border-zinc-500 disabled:opacity-40 px-5 py-2.5 text-sm transition-colors"
        >
          Send ping
        </button>
        <button
          onClick={sendEchoChunk}
          disabled={status !== "connected"}
          className="rounded-lg border border-zinc-700 hover:border-zinc-500 disabled:opacity-40 px-5 py-2.5 text-sm transition-colors"
        >
          Send 4KB echo chunk
        </button>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5 font-mono text-sm h-72 overflow-y-auto">
        {log.length === 0 ? (
          <p className="text-zinc-600">Events will appear here…</p>
        ) : (
          log.map((entry, i) => (
            <div key={i} className="mb-1.5">
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
    </main>
  );
}
