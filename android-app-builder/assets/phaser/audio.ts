// Procedural sound engine — all SFX synthesized at runtime via Web Audio.
// No asset files, zero network, crisp on every device.

let ctx: AudioContext | null = null
let master: GainNode | null = null
let muted = false

const MUTE_KEY = 'tapfly.muted'

function ac(): AudioContext {
  if (!ctx) {
    const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    ctx = new Ctor()
    master = ctx.createGain()
    master.gain.value = muted ? 0 : 0.9
    master.connect(ctx.destination)
  }
  return ctx
}

export function initAudio() {
  muted = localStorage.getItem(MUTE_KEY) === '1'
  ac()
}

// Browsers suspend audio until a user gesture — call this on first tap.
export function resumeAudio() {
  const c = ac()
  if (c.state === 'suspended') c.resume()
}

export function isMuted() {
  return muted
}

export function toggleMute(): boolean {
  muted = !muted
  localStorage.setItem(MUTE_KEY, muted ? '1' : '0')
  if (master) master.gain.linearRampToValueAtTime(muted ? 0 : 0.9, ac().currentTime + 0.05)
  return muted
}

function out(): GainNode {
  ac()
  return master as GainNode
}

function tone(
  freq: number,
  start: number,
  dur: number,
  type: OscillatorType,
  peak: number,
  freqEnd?: number,
) {
  const c = ac()
  const osc = c.createOscillator()
  const g = c.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, start)
  if (freqEnd !== undefined) osc.frequency.exponentialRampToValueAtTime(Math.max(1, freqEnd), start + dur)
  g.gain.setValueAtTime(0, start)
  g.gain.linearRampToValueAtTime(peak, start + 0.008)
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur)
  osc.connect(g)
  g.connect(out())
  osc.start(start)
  osc.stop(start + dur + 0.02)
}

function noise(start: number, dur: number, peak: number, filterType: BiquadFilterType, f0: number, f1: number) {
  const c = ac()
  const len = Math.floor(c.sampleRate * dur)
  const buffer = c.createBuffer(1, len, c.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1
  const src = c.createBufferSource()
  src.buffer = buffer
  const filter = c.createBiquadFilter()
  filter.type = filterType
  filter.frequency.setValueAtTime(f0, start)
  filter.frequency.exponentialRampToValueAtTime(Math.max(40, f1), start + dur)
  filter.Q.value = 1.2
  const g = c.createGain()
  g.gain.setValueAtTime(peak, start)
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur)
  src.connect(filter)
  filter.connect(g)
  g.connect(out())
  src.start(start)
  src.stop(start + dur + 0.02)
}

export function playFlap() {
  const t = ac().currentTime
  tone(420, t, 0.14, 'triangle', 0.22, 760)
  noise(t, 0.10, 0.10, 'bandpass', 1600, 700)
}

export function playScore(combo = 0) {
  const t = ac().currentTime
  // pitch climbs with combo for a satisfying streak feel
  const base = 660 * Math.pow(2, Math.min(combo, 7) / 12)
  tone(base, t, 0.12, 'square', 0.16)
  tone(base * 1.5, t + 0.06, 0.16, 'square', 0.16)
}

export function playMilestone() {
  const t = ac().currentTime
  const notes = [523.25, 659.25, 783.99, 1046.5] // C E G C — bright arpeggio
  notes.forEach((f, i) => tone(f, t + i * 0.07, 0.22, 'triangle', 0.18))
}

export function playCrash() {
  const t = ac().currentTime
  noise(t, 0.45, 0.35, 'lowpass', 2400, 120)
  tone(180, t, 0.5, 'sawtooth', 0.3, 50)
  tone(90, t + 0.02, 0.55, 'sine', 0.28, 40)
}

export function playSwoosh() {
  const t = ac().currentTime
  noise(t, 0.3, 0.18, 'bandpass', 400, 2200)
}

export function playButton() {
  const t = ac().currentTime
  tone(880, t, 0.08, 'square', 0.14)
}
