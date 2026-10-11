import { AGENT_WS_URL } from "./recorder";

export interface TurnMetrics {
  sttMs: number;
  llmFirstTokenMs: number | null;
  totalMs: number;
}

export interface AgentEvents {
  onReady: () => void;
  onModelLoading: () => void;
  onSpeechStart: () => void;
  onThinking: () => void;
  onSpeaking: () => void;
  onTranscript: (text: string, sttMs: number, audioMs: number) => void;
  onLlmDelta: (text: string) => void;
  onTurnDone: (metrics: TurnMetrics) => void;
  onInterrupted: () => void;
  onError: (reason: string) => void;
  onClose: () => void;
}

export class AgentClient {
  private ws: WebSocket | null = null;
  private events: AgentEvents;

  constructor(events: AgentEvents) {
    this.events = events;
  }

  connect(persona: string, onSendReady: () => void): void {
    const ws = new WebSocket(`${AGENT_WS_URL}?persona=${encodeURIComponent(persona)}`);
    ws.binaryType = "arraybuffer";
    this.ws = ws;

    ws.onopen = onSendReady;
    ws.onclose = () => this.events.onClose();
    ws.onerror = () => this.events.onError("Connection failed");
    ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data !== "string") return;
      const msg = JSON.parse(event.data);
      switch (msg.type) {
        case "model_status":
          this.events.onModelLoading();
          break;
        case "ready":
          this.events.onReady();
          break;
        case "speech_start":
          this.events.onSpeechStart();
          break;
        case "thinking":
          this.events.onThinking();
          break;
        case "speaking":
          this.events.onSpeaking();
          break;
        case "transcript":
          this.events.onTranscript(msg.text, msg.stt_ms, msg.audio_ms);
          break;
        case "llm_delta":
          this.events.onLlmDelta(msg.text);
          break;
        case "turn_done":
          this.events.onTurnDone({
            sttMs: msg.metrics.stt_ms,
            llmFirstTokenMs: msg.metrics.llm_first_token_ms,
            totalMs: msg.metrics.total_ms,
          });
          break;
        case "interrupted":
          this.events.onInterrupted();
          break;
        case "error":
          this.events.onError(msg.reason);
          break;
      }
    };
  }

  sendAudio(pcm: ArrayBuffer): void {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(pcm);
  }

  close(): void {
    this.ws?.close();
    this.ws = null;
  }
}

export class PcmPlayer {
  private ctx: AudioContext | null = null;
  private nextTime = 0;
  private sources = new Set<AudioBufferSourceNode>();

  start(): void {
    this.ctx = new AudioContext({ sampleRate: 24000 });
    this.nextTime = 0;
  }

  play(pcm: ArrayBuffer): void {
    if (!this.ctx) return;
    const floats = new Float32Array(pcm);
    if (floats.length === 0) return;
    const buffer = this.ctx.createBuffer(1, floats.length, this.ctx.sampleRate);
    buffer.copyToChannel(floats, 0);
    const source = this.ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.ctx.destination);

    const now = this.ctx.currentTime;
    if (this.nextTime < now + 0.02) this.nextTime = now + 0.02;
    source.start(this.nextTime);
    this.nextTime += buffer.duration;

    this.sources.add(source);
    source.onended = () => this.sources.delete(source);
  }

  stopAll(): void {
    for (const source of this.sources) {
      try {
        source.stop();
      } catch {
        void 0;
      }
    }
    this.sources.clear();
    this.nextTime = this.ctx?.currentTime ?? 0;
  }

  async close(): Promise<void> {
    this.stopAll();
    await this.ctx?.close();
    this.ctx = null;
  }
}
