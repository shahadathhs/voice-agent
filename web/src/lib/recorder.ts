const API_WS_URL = process.env.NEXT_PUBLIC_API_WS_URL ?? "ws://localhost:8000";
export const STT_WS_URL = `${API_WS_URL}/ws/stt`;
export const ECHO_WS_URL = `${API_WS_URL}/ws`;

export type ChunkHandler = (pcm: ArrayBuffer, level: number) => void;

function computeRms(pcm: ArrayBuffer): number {
  const samples = new Int16Array(pcm);
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) {
    const normalized = samples[i] / 32768;
    sum += normalized * normalized;
  }
  return Math.sqrt(sum / samples.length);
}

export class MicRecorder {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: AudioWorkletNode | null = null;

  onChunk: ChunkHandler | null = null;

  async start(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    this.ctx = new AudioContext({ sampleRate: 16000 });
    await this.ctx.audioWorklet.addModule("/worklets/recorder-worklet.js");

    const source = this.ctx.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.ctx, "recorder-processor");
    this.node.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
      this.onChunk?.(event.data, computeRms(event.data));
    };

    source.connect(this.node);
    this.node.connect(this.ctx.destination);
  }

  async stop(): Promise<void> {
    this.node?.port.close();
    this.node?.disconnect();
    this.stream?.getTracks().forEach((track) => track.stop());
    await this.ctx?.close();
    this.node = null;
    this.stream = null;
    this.ctx = null;
  }
}
