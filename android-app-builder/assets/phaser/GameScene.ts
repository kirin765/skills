import Phaser from 'phaser'
import { GAME_WIDTH, GAME_HEIGHT } from '../config'
import { buildTextures, GROUND_H, PIPE_W, CAP_W } from '../textures'
import {
  initAudio,
  resumeAudio,
  isMuted,
  toggleMute,
  playFlap,
  playScore,
  playMilestone,
  playCrash,
  playSwoosh,
  playButton,
} from '../audio'

const FLAP = -380
const PLAY_TOP = 0
const PLAY_BOTTOM = GAME_HEIGHT - GROUND_H
const BEST_KEY = 'tapfly.best'

type Pair = {
  top: Phaser.Types.Physics.Arcade.ImageWithDynamicBody
  parts: Phaser.GameObjects.Image[]
  scored: boolean
}

type Emitter = Phaser.GameObjects.Particles.ParticleEmitter

export class GameScene extends Phaser.Scene {
  private bird!: Phaser.Types.Physics.Arcade.SpriteWithDynamicBody
  private pipes!: Phaser.Physics.Arcade.Group
  private pairs: Pair[] = []

  private farHills!: Phaser.GameObjects.TileSprite
  private nearHills!: Phaser.GameObjects.TileSprite
  private ground!: Phaser.GameObjects.TileSprite
  private clouds: Phaser.GameObjects.Image[] = []

  private scoreText!: Phaser.GameObjects.Text
  private hintText!: Phaser.GameObjects.Text
  private titleGroup!: Phaser.GameObjects.Container
  private muteBtn!: Phaser.GameObjects.Image

  private puffs!: Emitter
  private sparks!: Emitter
  private debris!: Emitter
  private feathers!: Emitter

  private spawnTimer?: Phaser.Time.TimerEvent
  private bobTween?: Phaser.Tweens.Tween

  private score = 0
  private best = 0
  private state: 'ready' | 'playing' | 'dead' = 'ready'
  private deadAt = 0

  constructor() {
    super('game')
  }

  preload() {
    buildTextures(this)
    if (!this.anims.exists('flap')) {
      this.anims.create({
        key: 'flap',
        frames: [{ key: 'bird0' }, { key: 'bird1' }, { key: 'bird2' }],
        frameRate: 12,
        repeat: -1,
        yoyo: true,
      })
    }
  }

  create() {
    initAudio()
    this.score = 0
    this.pairs = []
    this.state = 'ready'
    this.best = Number(localStorage.getItem(BEST_KEY) || 0)

    this.cameras.main.setBackgroundColor('#8fd0f0')
    this.cameras.main.fadeIn(350, 12, 30, 50)

    this.buildBackground()
    this.buildBird()
    this.buildEmitters()

    this.pipes = this.physics.add.group({ allowGravity: false })
    this.physics.add.overlap(this.bird, this.pipes, () => this.die(), undefined, this)

    this.physics.world.setBounds(0, PLAY_TOP, GAME_WIDTH, PLAY_BOTTOM)
    this.bird.setCollideWorldBounds(true)
    this.bird.body.onWorldBounds = true
    this.physics.world.on('worldbounds', (_b: unknown, _up: boolean, down: boolean) => {
      if (down) this.die()
    })

    this.buildScoreUI()
    this.buildReadyScreen()
    this.buildMuteButton()

    this.input.on('pointerdown', this.onPointer, this)
    this.input.keyboard?.on('keydown-SPACE', this.onTap, this)

    this.physics.pause()
  }

  // ----- builders -----

  private buildBackground() {
    this.add.image(GAME_WIDTH / 2, GAME_HEIGHT / 2, 'sky').setDepth(0)
    this.add.image(GAME_WIDTH - 36, 70, 'sun').setDepth(1).setScale(0.85)

    this.farHills = this.add
      .tileSprite(GAME_WIDTH / 2, PLAY_BOTTOM - 110, GAME_WIDTH, 220, 'hills_far')
      .setOrigin(0.5, 0)
      .setDepth(2)
      .setY(PLAY_BOTTOM - 150)
    this.nearHills = this.add
      .tileSprite(GAME_WIDTH / 2, PLAY_BOTTOM - 80, GAME_WIDTH, 220, 'hills_near')
      .setOrigin(0.5, 0)
      .setDepth(3)
      .setY(PLAY_BOTTOM - 130)

    for (let i = 0; i < 4; i++) {
      const c = this.add
        .image(Phaser.Math.Between(0, GAME_WIDTH), Phaser.Math.Between(50, 220), i % 2 ? 'cloud0' : 'cloud1')
        .setDepth(4)
        .setAlpha(0.9)
        .setScale(Phaser.Math.FloatBetween(0.6, 1.1))
      this.clouds.push(c)
    }

    this.ground = this.add
      .tileSprite(GAME_WIDTH / 2, PLAY_BOTTOM, GAME_WIDTH, GROUND_H, 'ground')
      .setOrigin(0.5, 0)
      .setDepth(6)
  }

  private buildBird() {
    this.bird = this.physics.add.sprite(GAME_WIDTH * 0.3, GAME_HEIGHT * 0.42, 'bird0')
    this.bird.setDepth(7)
    this.bird.setCircle(15, 5, 5)
    this.bird.play('flap')
  }

  private buildEmitters() {
    this.puffs = this.add
      .particles(0, 0, 'puff', {
        speed: { min: 20, max: 70 },
        angle: { min: 150, max: 210 },
        scale: { start: 0.7, end: 0 },
        alpha: { start: 0.5, end: 0 },
        lifespan: 450,
        gravityY: 60,
        emitting: false,
      })
      .setDepth(8)

    this.sparks = this.add
      .particles(0, 0, 'spark', {
        speed: { min: 90, max: 240 },
        scale: { start: 0.8, end: 0 },
        lifespan: 600,
        blendMode: 'ADD',
        emitting: false,
      })
      .setDepth(9)

    this.debris = this.add
      .particles(0, 0, 'spark', {
        speed: { min: 120, max: 320 },
        scale: { start: 1, end: 0 },
        lifespan: 700,
        gravityY: 500,
        blendMode: 'ADD',
        emitting: false,
      })
      .setDepth(9)

    this.feathers = this.add
      .particles(0, 0, 'feather', {
        speed: { min: 60, max: 200 },
        scale: { start: 1, end: 0.6 },
        alpha: { start: 1, end: 0 },
        rotate: { min: 0, max: 360 },
        lifespan: 900,
        gravityY: 320,
        emitting: false,
      })
      .setDepth(9)
  }

  private buildScoreUI() {
    this.scoreText = this.add
      .text(GAME_WIDTH / 2, 78, '0', {
        fontFamily: 'Arial Black, Arial, sans-serif',
        fontSize: '60px',
        color: '#ffffff',
        stroke: '#3a2c1a',
        strokeThickness: 8,
      })
      .setOrigin(0.5)
      .setDepth(20)
      .setShadow(0, 5, 'rgba(0,0,0,0.35)', 6)
      .setScale(0)
  }

  private buildReadyScreen() {
    this.titleGroup = this.add.container(0, 0).setDepth(21)

    const title = this.add
      .text(GAME_WIDTH / 2, GAME_HEIGHT * 0.26, 'TAP FLY', {
        fontFamily: 'Arial Black, Arial, sans-serif',
        fontSize: '52px',
        color: '#ffd166',
        stroke: '#3a2c1a',
        strokeThickness: 9,
      })
      .setOrigin(0.5)
      .setShadow(0, 6, 'rgba(0,0,0,0.4)', 8)

    const bestBadge = this.add
      .text(GAME_WIDTH / 2, GAME_HEIGHT * 0.26 + 46, `최고 기록  ${this.best}`, {
        fontFamily: 'Arial, sans-serif',
        fontSize: '18px',
        color: '#ffffff',
        stroke: '#3a2c1a',
        strokeThickness: 4,
      })
      .setOrigin(0.5)

    this.hintText = this.add
      .text(GAME_WIDTH / 2, GAME_HEIGHT * 0.66, '탭하여 시작', {
        fontFamily: 'Arial, sans-serif',
        fontSize: '24px',
        color: '#ffffff',
        stroke: '#3a2c1a',
        strokeThickness: 5,
      })
      .setOrigin(0.5)

    this.titleGroup.add([title, bestBadge, this.hintText])

    this.tweens.add({ targets: title, y: title.y - 10, duration: 1100, yoyo: true, repeat: -1, ease: 'Sine.inOut' })
    this.tweens.add({ targets: this.hintText, alpha: 0.25, duration: 700, yoyo: true, repeat: -1, ease: 'Sine.inOut' })

    this.bobTween = this.tweens.add({
      targets: this.bird,
      y: this.bird.y + 14,
      duration: 700,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.inOut',
    })
  }

  private buildMuteButton() {
    this.muteBtn = this.add
      .image(GAME_WIDTH - 26, 28, isMuted() ? 'speaker_off' : 'speaker_on')
      .setDepth(30)
      .setInteractive({ useHandCursor: true })
    this.muteBtn.on('pointerdown', (p: Phaser.Input.Pointer) => {
      p.event?.stopPropagation?.()
      const m = toggleMute()
      this.muteBtn.setTexture(m ? 'speaker_off' : 'speaker_on')
      if (!m) {
        resumeAudio()
        playButton()
      }
      this.tweens.add({ targets: this.muteBtn, scale: 0.85, duration: 80, yoyo: true })
    })
  }

  // ----- input -----

  private onPointer(pointer: Phaser.Input.Pointer) {
    if (this.muteBtn.getBounds().contains(pointer.x, pointer.y)) return
    this.onTap()
  }

  private onTap() {
    resumeAudio()
    if (this.state === 'dead') {
      if (this.time.now - this.deadAt > 600) this.restart()
      return
    }
    if (this.state === 'ready') this.startGame()
    this.flap()
  }

  private startGame() {
    this.state = 'playing'
    this.physics.resume()
    this.bobTween?.stop()
    this.tweens.add({ targets: this.titleGroup, alpha: 0, y: -30, duration: 250, onComplete: () => this.titleGroup.destroy() })
    this.tweens.add({ targets: this.scoreText, scale: 1, duration: 200, ease: 'Back.out' })
    this.spawnPipes()
    this.scheduleSpawn()
  }

  private flap() {
    if (this.state !== 'playing') return
    this.bird.setVelocityY(FLAP)
    this.puffs.explode(4, this.bird.x - 14, this.bird.y + 6)
    playFlap()
  }

  // ----- difficulty curve -----

  private get level() {
    return Math.floor(this.score / 5)
  }
  private get gap() {
    return Math.max(132, 176 - this.level * 6)
  }
  private get pipeSpeed() {
    return -(155 + Math.min(this.level * 12, 110))
  }
  private get spawnDelay() {
    return Math.max(1000, 1500 - this.level * 55)
  }

  private scheduleSpawn() {
    this.spawnTimer?.remove()
    this.spawnTimer = this.time.addEvent({
      delay: this.spawnDelay,
      callback: () => {
        if (this.state !== 'playing') return
        this.spawnPipes()
        this.scheduleSpawn()
      },
    })
  }

  private spawnPipes() {
    if (this.state !== 'playing') return
    const gap = this.gap
    const margin = 60
    const gapY = Phaser.Math.Between(margin + gap / 2, PLAY_BOTTOM - margin - gap / 2)
    const x = GAME_WIDTH + CAP_W
    const speed = this.pipeSpeed

    const mk = (px: number, py: number, key: string, oy: number) => {
      const img = this.pipes.create(px, py, key) as Phaser.Types.Physics.Arcade.ImageWithDynamicBody
      img.setOrigin(0.5, oy).setDepth(5)
      img.body.setAllowGravity(false)
      img.body.setVelocityX(speed)
      img.body.setImmovable(true)
      return img
    }

    const topBody = mk(x, gapY - gap / 2, 'pipe_body', 1)
    topBody.setDisplaySize(PIPE_W, GAME_HEIGHT)
    const topCap = mk(x, gapY - gap / 2, 'pipe_cap', 1)
    const botBody = mk(x, gapY + gap / 2, 'pipe_body', 0)
    botBody.setDisplaySize(PIPE_W, GAME_HEIGHT)
    const botCap = mk(x, gapY + gap / 2, 'pipe_cap', 0)

    this.pairs.push({ top: topBody, parts: [topBody, topCap, botBody, botCap], scored: false })
  }

  // ----- main loop -----

  update(_t: number, delta: number) {
    const d = delta / 16.666

    // parallax — alive even on the ready screen
    this.farHills.tilePositionX += 0.2 * d
    this.nearHills.tilePositionX += 0.5 * d
    this.clouds.forEach((c) => {
      c.x -= 0.25 * d * c.scale
      if (c.x < -80) {
        c.x = GAME_WIDTH + 80
        c.y = Phaser.Math.Between(50, 220)
      }
    })

    if (this.state === 'playing') {
      this.ground.tilePositionX += (-this.pipeSpeed / 60) * d

      // velocity-driven tilt
      const target = Phaser.Math.Clamp(this.bird.body.velocity.y * 0.09, -22, 80)
      this.bird.angle = Phaser.Math.Linear(this.bird.angle, target, 0.12 * d)

      for (let i = this.pairs.length - 1; i >= 0; i--) {
        const pair = this.pairs[i]
        if (!pair.scored && pair.top.x < this.bird.x) {
          pair.scored = true
          this.addScore()
        }
        if (pair.top.x < -CAP_W) {
          pair.parts.forEach((p) => p.destroy())
          this.pairs.splice(i, 1)
        }
      }
    }
  }

  // ----- scoring -----

  private addScore() {
    this.score++
    this.scoreText.setText(String(this.score))
    this.tweens.add({
      targets: this.scoreText,
      scale: 1.35,
      duration: 90,
      yoyo: true,
      ease: 'Quad.out',
    })
    this.sparks.explode(8, this.scoreText.x, this.scoreText.y)

    if (this.score % 10 === 0) {
      playMilestone()
      this.cameras.main.flash(180, 255, 240, 180)
      this.sparks.explode(20, this.scoreText.x, this.scoreText.y)
      this.floatText(GAME_WIDTH / 2, GAME_HEIGHT * 0.4, `${this.score} 연속!`, '#ffd166')
    } else {
      playScore(this.score)
    }
  }

  private floatText(x: number, y: number, msg: string, color: string) {
    const t = this.add
      .text(x, y, msg, {
        fontFamily: 'Arial Black, Arial, sans-serif',
        fontSize: '30px',
        color,
        stroke: '#3a2c1a',
        strokeThickness: 6,
      })
      .setOrigin(0.5)
      .setDepth(22)
    this.tweens.add({
      targets: t,
      y: y - 60,
      alpha: 0,
      scale: 1.4,
      duration: 900,
      ease: 'Quad.out',
      onComplete: () => t.destroy(),
    })
  }

  // ----- death & game over -----

  private die() {
    if (this.state !== 'playing') return
    this.state = 'dead'
    this.deadAt = this.time.now
    this.spawnTimer?.remove()

    playCrash()
    this.cameras.main.shake(260, 0.012)
    this.cameras.main.flash(140, 255, 80, 60)
    this.debris.explode(26, this.bird.x, this.bird.y)
    this.feathers.explode(12, this.bird.x, this.bird.y)

    this.physics.pause()
    this.bird.stop()
    this.bird.setTexture('bird1')

    // bird tumbles to the ground
    this.tweens.add({
      targets: this.bird,
      y: PLAY_BOTTOM - 12,
      angle: 110,
      duration: 520,
      ease: 'Quad.in',
      onComplete: () => this.showGameOver(),
    })
  }

  private showGameOver() {
    playSwoosh()
    // Optional integration point: call an ads/analytics/leaderboard hook here.
    const isRecord = this.score > this.best
    if (isRecord) {
      this.best = this.score
      localStorage.setItem(BEST_KEY, String(this.best))
    }

    const cx = GAME_WIDTH / 2
    const panel = this.add.container(cx, GAME_HEIGHT * 0.42).setDepth(25).setScale(0)

    const g = this.add.graphics()
    const w = 280
    const h = 230
    g.fillStyle(0x000000, 0.25)
    g.fillRoundedRect(-w / 2 + 4, -h / 2 + 6, w, h, 22)
    g.fillStyle(0xfff7e6, 1)
    g.fillRoundedRect(-w / 2, -h / 2, w, h, 22)
    g.lineStyle(4, 0xffd166, 1)
    g.strokeRoundedRect(-w / 2, -h / 2, w, h, 22)

    const over = this.add
      .text(0, -h / 2 + 34, 'GAME OVER', {
        fontFamily: 'Arial Black, Arial, sans-serif',
        fontSize: '32px',
        color: '#e76f51',
        stroke: '#ffffff',
        strokeThickness: 4,
      })
      .setOrigin(0.5)

    const medalKey = this.medalFor(this.score)
    const medal = medalKey ? this.add.image(-78, 6, medalKey).setScale(1.05) : null

    const scoreLabel = this.add
      .text(20, -16, '점수', { fontFamily: 'Arial, sans-serif', fontSize: '15px', color: '#8a7a5c' })
      .setOrigin(0.5)
    const scoreVal = this.add
      .text(20, 8, String(this.score), {
        fontFamily: 'Arial Black, Arial, sans-serif',
        fontSize: '34px',
        color: '#3a2c1a',
      })
      .setOrigin(0.5)
    const bestLabel = this.add
      .text(20, 36, `최고  ${this.best}`, { fontFamily: 'Arial, sans-serif', fontSize: '15px', color: '#8a7a5c' })
      .setOrigin(0.5)

    panel.add([g, over, scoreLabel, scoreVal, bestLabel])
    if (medal) panel.add(medal)

    if (isRecord) {
      const badge = this.add
        .text(60, -h / 2 + 70, 'NEW!', {
          fontFamily: 'Arial Black, Arial, sans-serif',
          fontSize: '20px',
          color: '#ffffff',
          backgroundColor: '#e76f51',
          padding: { x: 6, y: 3 },
        })
        .setOrigin(0.5)
        .setAngle(-12)
      panel.add(badge)
      this.tweens.add({ targets: badge, scale: 1.15, duration: 450, yoyo: true, repeat: -1, ease: 'Sine.inOut' })
    }

    const restart = this.add
      .text(0, h / 2 - 30, '탭하여 재시작', {
        fontFamily: 'Arial Black, Arial, sans-serif',
        fontSize: '20px',
        color: '#ffffff',
        backgroundColor: '#2a9d8f',
        padding: { x: 16, y: 8 },
      })
      .setOrigin(0.5)
    panel.add(restart)
    this.tweens.add({ targets: restart, scale: 1.06, duration: 600, yoyo: true, repeat: -1, ease: 'Sine.inOut' })

    this.tweens.add({ targets: panel, scale: 1, duration: 420, ease: 'Back.out' })
    if (medal) {
      medal.setScale(0)
      this.tweens.add({ targets: medal, scale: 1.05, delay: 300, duration: 400, ease: 'Back.out' })
      this.sparks.explode(14, panel.x - 78, panel.y + 6)
    }
  }

  private medalFor(score: number): string | null {
    if (score >= 40) return 'medal_platinum'
    if (score >= 25) return 'medal_gold'
    if (score >= 12) return 'medal_silver'
    if (score >= 5) return 'medal_bronze'
    return null
  }

  private restart() {
    playButton()
    this.cameras.main.fadeOut(220, 12, 30, 50)
    this.cameras.main.once('camerafadeoutcomplete', () => this.scene.restart())
  }
}
