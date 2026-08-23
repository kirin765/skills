// Unattended TikTok upload against a per-account persistent profile.
//   node upload.mjs --account <name> --video path.mp4 --caption "text" \
//     [--ai-label] [--visibility public|friends|private] [--dry-run]
import { existsSync } from 'node:fs'
import { openContext, isLoggedIn, uploadClip } from './lib/tiktok.mjs'

const argv = process.argv.slice(2)
function opt(name) {
  const i = argv.indexOf(name)
  return i === -1 ? undefined : argv[i + 1]
}
const account = opt('--account')
const video = opt('--video')
const caption = opt('--caption') ?? ''
const aiLabel = argv.includes('--ai-label')
const visibility = opt('--visibility') ?? null
const dryRun = argv.includes('--dry-run')

if (!account || !video) {
  console.error(
    'usage: node upload.mjs --account <name> --video path.mp4 [--caption "text"] [--ai-label] [--visibility public|friends|private] [--dry-run]'
  )
  process.exit(2)
}
if (!existsSync(video)) {
  console.error('video not found:', video)
  process.exit(2)
}
if (visibility && !['public', 'friends', 'private'].includes(visibility)) {
  console.error('--visibility must be one of: public friends private')
  process.exit(2)
}

const ctx = await openContext(account, { headless: false })
try {
  if (!(await isLoggedIn(ctx))) {
    console.error(`❌ '${account}' 로그인 안 됨 — 먼저: node login.mjs --account ${account}`)
    process.exit(1)
  }
  const res = await uploadClip(ctx, { video, caption, aiLabel, visibility, dryRun })
  console.log(JSON.stringify(res))
  process.exit(res.ok ? 0 : 1)
} catch (err) {
  console.error('❌ upload failed:', err.message)
  process.exit(1)
} finally {
  await ctx.close().catch(() => {})
}
