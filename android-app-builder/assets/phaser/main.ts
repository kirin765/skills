import './style.css'
import Phaser from 'phaser'
import { GAME_WIDTH, GAME_HEIGHT } from './config'
import { GameScene } from './scenes/GameScene'

export { GAME_WIDTH, GAME_HEIGHT }

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  backgroundColor: '#8fd0f0',
  width: GAME_WIDTH,
  height: GAME_HEIGHT,
  render: {
    antialias: true,
    roundPixels: false,
    powerPreference: 'high-performance',
  },
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
  physics: {
    default: 'arcade',
    arcade: { gravity: { x: 0, y: 1200 } },
  },
  scene: [GameScene],
})

if (import.meta.env.DEV) {
  ;(window as unknown as { game: Phaser.Game }).game = game
}
