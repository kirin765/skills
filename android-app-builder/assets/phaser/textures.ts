import Phaser from 'phaser'
import { GAME_WIDTH, GAME_HEIGHT } from './config'

export const GROUND_H = 96
export const PIPE_W = 62
export const CAP_W = PIPE_W + 14
export const CAP_H = 30

type G = Phaser.GameObjects.Graphics

function tex(scene: Phaser.Scene, key: string, w: number, h: number, draw: (g: G) => void) {
  const g = scene.make.graphics({ x: 0, y: 0 }, false)
  draw(g)
  g.generateTexture(key, w, h)
  g.destroy()
}

function starPoints(cx: number, cy: number, outer: number, inner: number, points = 5): number[] {
  const pts: number[] = []
  const step = Math.PI / points
  let a = -Math.PI / 2
  for (let i = 0; i < points * 2; i++) {
    const r = i % 2 === 0 ? outer : inner
    pts.push(cx + Math.cos(a) * r, cy + Math.sin(a) * r)
    a += step
  }
  return pts
}

function drawBird(g: G, wingY: number) {
  // body
  g.fillStyle(0xffd166, 1)
  g.fillCircle(20, 20, 15)
  // belly highlight
  g.fillStyle(0xffe49b, 1)
  g.fillCircle(18, 24, 8)
  // body shading (lower-right)
  g.fillStyle(0xf2b138, 0.5)
  g.slice(20, 20, 15, Phaser.Math.DegToRad(20), Phaser.Math.DegToRad(150), false)
  g.fillPath()
  // outline
  g.lineStyle(2, 0xd99b2f, 1)
  g.strokeCircle(20, 20, 15)
  // wing
  g.fillStyle(0xf4a93c, 1)
  g.fillEllipse(15, wingY, 17, 10)
  g.lineStyle(1.5, 0xcf8a26, 1)
  g.strokeEllipse(15, wingY, 17, 10)
  // eye
  g.fillStyle(0xffffff, 1)
  g.fillCircle(27, 15, 5.5)
  g.fillStyle(0x222222, 1)
  g.fillCircle(29, 15, 2.8)
  g.fillStyle(0xffffff, 1)
  g.fillCircle(28, 14, 1.2)
  // beak
  g.fillStyle(0xf4761e, 1)
  g.fillTriangle(32, 16, 44, 20, 32, 24)
  g.lineStyle(1.5, 0xc85d12, 1)
  g.strokeTriangle(32, 16, 44, 20, 32, 24)
}

function drawMedal(g: G, rim: number, inner: number, innerDark: number) {
  g.fillStyle(rim, 1)
  g.fillCircle(28, 28, 26)
  g.fillStyle(inner, 1)
  g.fillCircle(28, 28, 20)
  g.fillStyle(innerDark, 0.5)
  g.slice(28, 28, 20, Phaser.Math.DegToRad(20), Phaser.Math.DegToRad(160), false)
  g.fillPath()
  // ribbon dots / rivets
  g.fillStyle(0xffffff, 0.35)
  g.fillCircle(20, 18, 4)
  // star
  g.fillStyle(0xffffff, 0.92)
  g.fillPoints(toPoints(starPoints(28, 29, 12, 5)), true)
}

function toPoints(flat: number[]): Phaser.Math.Vector2[] {
  const out: Phaser.Math.Vector2[] = []
  for (let i = 0; i < flat.length; i += 2) out.push(new Phaser.Math.Vector2(flat[i], flat[i + 1]))
  return out
}

function softCircle(g: G, cx: number, cy: number, r: number, color: number, steps = 8) {
  for (let i = steps; i >= 1; i--) {
    g.fillStyle(color, 0.16 * (1 - i / (steps + 2)) + 0.04)
    g.fillCircle(cx, cy, (r * i) / steps)
  }
}

export function buildTextures(scene: Phaser.Scene) {
  // ---- sky gradient ----
  tex(scene, 'sky', GAME_WIDTH, GAME_HEIGHT, (g) => {
    g.fillGradientStyle(0x2c6fb5, 0x2c6fb5, 0x8fd0f0, 0xbfe9ff, 1)
    g.fillRect(0, 0, GAME_WIDTH, GAME_HEIGHT)
  })

  // ---- sun glow ----
  tex(scene, 'sun', 220, 220, (g) => {
    softCircle(g, 110, 110, 105, 0xfff6d0, 10)
    g.fillStyle(0xfffbe6, 0.95)
    g.fillCircle(110, 110, 42)
  })

  // ---- clouds ----
  const cloud = (key: string, blobs: [number, number, number][]) =>
    tex(scene, key, 140, 70, (g) => {
      g.fillStyle(0xffffff, 0.92)
      blobs.forEach(([x, y, r]) => g.fillCircle(x, y, r))
      g.fillStyle(0xe6f3ff, 0.9)
      blobs.forEach(([x, y, r]) => g.fillCircle(x, y + 6, r * 0.8))
    })
  cloud('cloud0', [[40, 40, 22], [66, 32, 26], [92, 42, 20], [70, 46, 24]])
  cloud('cloud1', [[35, 42, 18], [60, 34, 22], [85, 44, 17]])

  // ---- hills (tileable) ----
  const hill = (key: string, color: number, amp: number, baseY: number) =>
    tex(scene, key, GAME_WIDTH, 220, (g) => {
      g.fillStyle(color, 1)
      g.beginPath()
      g.moveTo(0, 220)
      for (let x = 0; x <= GAME_WIDTH; x += 4) {
        const y =
          baseY -
          Math.sin((x / GAME_WIDTH) * Math.PI * 2) * amp -
          Math.sin((x / GAME_WIDTH) * Math.PI * 6) * (amp * 0.35)
        g.lineTo(x, y)
      }
      g.lineTo(GAME_WIDTH, 220)
      g.closePath()
      g.fillPath()
    })
  hill('hills_far', 0x9fd9b0, 26, 110)
  hill('hills_near', 0x66bd7a, 38, 80)

  // ---- ground (tileable strip) ----
  tex(scene, 'ground', 48, GROUND_H, (g) => {
    // dirt
    g.fillStyle(0xd9a566, 1)
    g.fillRect(0, 14, 48, GROUND_H - 14)
    g.fillStyle(0xc8924f, 1)
    for (let i = 0; i < 14; i++) {
      const x = (i * 37) % 48
      const y = 24 + ((i * 53) % (GROUND_H - 30))
      g.fillCircle(x, y, 2.4)
    }
    // grass top band
    g.fillStyle(0x6ab04c, 1)
    g.fillRect(0, 0, 48, 16)
    g.fillStyle(0x589b3d, 1)
    g.fillRect(0, 12, 48, 4)
    // grass blades (repeat over 48)
    g.fillStyle(0x7cc35a, 1)
    for (let x = 0; x < 48; x += 8) {
      g.fillTriangle(x, 16, x + 4, 4, x + 8, 16)
    }
  })

  // ---- pipe body (stretched vertically; gradient is horizontal) ----
  tex(scene, 'pipe_body', PIPE_W, 80, (g) => {
    g.fillStyle(0x3cab8f, 1)
    g.fillRect(0, 0, PIPE_W, 80)
    g.fillStyle(0x6fd9bb, 0.9) // highlight stripe
    g.fillRect(8, 0, 12, 80)
    g.fillStyle(0xbff0e2, 0.5)
    g.fillRect(10, 0, 5, 80)
    g.fillStyle(0x247a63, 1) // right shadow
    g.fillRect(PIPE_W - 9, 0, 9, 80)
    g.fillStyle(0x1f6b56, 1) // edges
    g.fillRect(0, 0, 3, 80)
    g.fillRect(PIPE_W - 3, 0, 3, 80)
  })

  // ---- pipe cap ----
  tex(scene, 'pipe_cap', CAP_W, CAP_H, (g) => {
    g.fillStyle(0x1f6b56, 1)
    g.fillRoundedRect(0, 0, CAP_W, CAP_H, 7)
    g.fillStyle(0x3cab8f, 1)
    g.fillRoundedRect(2, 2, CAP_W - 4, CAP_H - 4, 6)
    g.fillStyle(0x6fd9bb, 0.95)
    g.fillRect(9, 4, 12, CAP_H - 8)
    g.fillStyle(0xbff0e2, 0.5)
    g.fillRect(11, 4, 5, CAP_H - 8)
    g.fillStyle(0x247a63, 1)
    g.fillRect(CAP_W - 12, 4, 8, CAP_H - 8)
    g.fillStyle(0xffffff, 0.18)
    g.fillRect(4, 4, CAP_W - 8, 3)
  })

  // ---- bird flap frames ----
  tex(scene, 'bird0', 48, 40, (g) => drawBird(g, 13)) // wing up
  tex(scene, 'bird1', 48, 40, (g) => drawBird(g, 20)) // wing mid
  tex(scene, 'bird2', 48, 40, (g) => drawBird(g, 27)) // wing down

  // ---- particles ----
  tex(scene, 'spark', 16, 16, (g) => softCircle(g, 8, 8, 7, 0xffffff, 6))
  tex(scene, 'puff', 18, 18, (g) => softCircle(g, 9, 9, 8, 0xffffff, 6))
  tex(scene, 'feather', 12, 8, (g) => {
    g.fillStyle(0xffd166, 1)
    g.fillEllipse(6, 4, 11, 6)
  })
  tex(scene, 'star', 22, 22, (g) => {
    g.fillStyle(0xfff2a8, 1)
    g.fillPoints(toPoints(starPoints(11, 11, 10, 4)), true)
  })

  // ---- mute / sound icons ----
  const speaker = (key: string, on: boolean) =>
    tex(scene, key, 40, 40, (g) => {
      g.fillStyle(0xffffff, 0.9)
      g.fillCircle(20, 20, 17)
      g.lineStyle(2, 0x2a9d8f, 0.95)
      g.strokeCircle(20, 20, 17)
      g.fillStyle(0x2a4d45, 1)
      g.fillRect(11, 16, 5, 9)
      g.beginPath()
      g.moveTo(15, 16)
      g.lineTo(22, 10)
      g.lineTo(22, 30)
      g.lineTo(15, 24)
      g.closePath()
      g.fillPath()
      if (on) {
        g.lineStyle(2.4, 0x2a4d45, 1)
        g.beginPath()
        g.arc(24, 20, 5, -0.7, 0.7)
        g.strokePath()
        g.beginPath()
        g.arc(24, 20, 9, -0.7, 0.7)
        g.strokePath()
      } else {
        g.lineStyle(2.8, 0xe76f51, 1)
        g.lineBetween(26, 14, 33, 26)
        g.lineBetween(33, 14, 26, 26)
      }
    })
  speaker('speaker_on', true)
  speaker('speaker_off', false)

  // ---- medals ----
  tex(scene, 'medal_bronze', 56, 56, (g) => drawMedal(g, 0xa9701f, 0xe0954a, 0x9c5f1e))
  tex(scene, 'medal_silver', 56, 56, (g) => drawMedal(g, 0x8a96a3, 0xd6dee6, 0x9aa6b2))
  tex(scene, 'medal_gold', 56, 56, (g) => drawMedal(g, 0xc7991a, 0xffd84d, 0xd9a915))
  tex(scene, 'medal_platinum', 56, 56, (g) => drawMedal(g, 0x4fb0c4, 0xc4f0f7, 0x7fd4e0))
}
