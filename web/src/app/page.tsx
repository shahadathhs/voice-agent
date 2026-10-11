import Link from "next/link";

const pipeline = [
  { label: "Mic", detail: "AudioWorklet · 16kHz PCM" },
  { label: "VAD", detail: "Silero turn detection" },
  { label: "STT", detail: "faster-whisper int8" },
  { label: "LLM", detail: "Groq streaming" },
  { label: "TTS", detail: "Kokoro neural" },
  { label: "Speaker", detail: "streamed 24kHz" },
];

const features = [
  {
    title: "Natural turn-taking",
    body: "Silero VAD detects when you finish speaking. No push-to-talk, no buttons — just talk like you would to a person.",
  },
  {
    title: "Barge-in",
    body: "Interrupt the agent mid-sentence. The LLM stream cancels, playback stops instantly, and it starts listening again.",
  },
  {
    title: "Sentence-chunked TTS",
    body: "Speech starts on the first complete sentence while the LLM is still generating — no waiting for the full reply.",
  },
  {
    title: "Local speech models",
    body: "Whisper and Kokoro run on-device in Docker. Only the LLM call leaves the machine, via Groq's free tier.",
  },
];

export default function Home() {
  return (
    <main>
      <nav className="border-b border-zinc-800">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="font-mono font-semibold text-lg">voice-agent</span>
          <div className="flex items-center gap-6 text-sm text-zinc-400">
            <Link href="/agent" className="hover:text-zinc-100 transition-colors">
              Live demo
            </Link>
            <Link href="/play" className="hover:text-zinc-100 transition-colors">
              Playground
            </Link>
            <a
              href="https://github.com/shahadathhs/voice-agent"
              target="_blank"
              rel="noreferrer"
              className="hover:text-zinc-100 transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </nav>

      <section className="max-w-5xl mx-auto px-6 pt-24 pb-16 text-center">
        <p className="font-mono text-sm text-emerald-400 mb-4">
          open source · streaming · barge-in · local models
        </p>
        <h1 className="text-5xl md:text-6xl font-semibold tracking-tight mb-6">
          Talk to AI.
          <br />
          <span className="text-zinc-500">It talks back. Instantly.</span>
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl mx-auto mb-10">
          A real-time voice agent: streaming speech recognition, LLM orchestration and neural
          text-to-speech with natural turn-taking and interruption support — built from scratch
          on WebSockets.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link
            href="/agent"
            className="rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-medium px-6 py-3 transition-colors"
          >
            Start talking →
          </Link>
          <a
            href="https://github.com/shahadathhs/voice-agent"
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-zinc-700 hover:border-zinc-500 px-6 py-3 transition-colors"
          >
            View source
          </a>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-semibold mb-10 text-center">The pipeline</h2>
        <div className="flex flex-wrap items-center justify-center gap-3">
          {pipeline.map((stage, i) => (
            <div key={stage.label} className="flex items-center gap-3">
              <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4 min-w-36">
                <div className="font-mono font-semibold text-emerald-400">{stage.label}</div>
                <div className="text-xs text-zinc-500 mt-1">{stage.detail}</div>
              </div>
              {i < pipeline.length - 1 && <span className="text-zinc-600">→</span>}
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-2 gap-6">
          {features.map((f) => (
            <div key={f.title} className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-8">
              <h3 className="font-semibold text-lg mb-3">{f.title}</h3>
              <p className="text-zinc-400 text-sm leading-relaxed">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-16">
        <div className="rounded-2xl border border-zinc-800 bg-gradient-to-br from-zinc-900 to-zinc-950 p-10 text-center">
          <h2 className="text-2xl font-semibold mb-4">Latency is the product</h2>
          <p className="text-zinc-400 text-sm max-w-xl mx-auto mb-8">
            Every stage is instrumented. The live demo shows real per-turn numbers measured in
            your browser — speech end to first audio, updated every turn.
          </p>
          <Link
            href="/agent"
            className="rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-medium px-6 py-3 transition-colors"
          >
            See it live →
          </Link>
        </div>
      </section>

      <footer className="border-t border-zinc-800 mt-16">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between text-sm text-zinc-500">
          <span>voice-agent</span>
          <span className="font-mono text-xs">
            FastAPI · WebSockets · Silero VAD · faster-whisper · Groq · Kokoro · Next.js
          </span>
        </div>
      </footer>
    </main>
  );
}
