// One-time interactive login into a per-account profile. Run at the machine —
// handles 2FA. After this, upload.mjs runs unattended against the same profile.
//   node login.mjs --account <name>
import { openContext, isLoggedIn, profileDir } from './lib/tiktok.mjs'

const args = process.argv.slice(2)
const account = args[args.indexOf('--account') + 1]
if (!args.includes('--account') || !account) {
  console.error('usage: node login.mjs --account <name>')
  process.exit(2)
}

console.log('profile:', profileDir(account))
const ctx = await openContext(account, { headless: false })
const page = ctx.pages()[0] || (await ctx.newPage())
await page.goto('https://www.tiktok.com/login')
console.log(`\n>>> 브라우저에서 '${account}' 계정으로 로그인하세요 (2FA 포함).`)
console.log('>>> 로그인 완료되면 자동 감지 후 창이 닫힙니다.\n')

for (let i = 0; i < 600; i++) {
  if (await isLoggedIn(ctx)) {
    console.log('✅ 로그인 감지 — 세션 저장됨. 이제 무인 업로드 가능.')
    await ctx.close()
    process.exit(0)
  }
  await page.waitForTimeout(2000)
}
console.log('⏱ 타임아웃 — 로그인 안 됨.')
await ctx.close()
process.exit(1)
