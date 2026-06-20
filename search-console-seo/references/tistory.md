# Editing a Tistory post for Naver/Google search

Tistory is external content — you optimize it in the browser via the extension,
not in code. A Tistory blog already auto-generates a sitemap and can be verified
in both Search Advisor and GSC, so per-post work is about the on-page signals.

## Which Tistory fields map to which search signal

Open the post in the editor (`https://<blog>.tistory.com/manage/post/<id>` or
Manage → 글관리 → edit). The levers, in priority order:

- **제목 (title)** → `<title>` + `og:title`. Front-load the primary Korean
  keyword; keep it natural, not stuffed.
- **본문 첫 문단 (first paragraph)** → Tistory derives the meta description /
  `og:description` from the opening text. Put the keyword + the value
  proposition in the first 1–2 sentences. There is no separate per-post
  meta-description field by default, so the lead paragraph *is* the description.
- **대표 이미지 (representative image)** → `og:image`. Set one (글 설정 / 더보기
  → 대표 이미지). Without it the Naver/Google snippet has no thumbnail. Use a
  ≥1200px-wide image.
- **태그 (tags)** → Naver blog/web search uses tags. Add 3–6 specific tags
  matching real search queries, not generic ones.
- **본문 구조** → real `<h2>/<h3>` headings (use the editor's heading styles,
  not bold text), `<a href>` links with descriptive anchor text, image `alt`.
- **글 주소 (slug)** → a clean keyword URL helps, BUT changing the slug of a
  published post breaks existing inbound links and resets its index history.
  Only change it on a brand-new or unindexed post; otherwise leave it.

## Editing without corrupting the body

Tistory's editor is TinyMCE. Prefer **surgical edits** — change the title, fix
the first paragraph, add tags, set the representative image, add an alt text —
over wholesale body replacement, which risks reflowing or breaking existing
formatting. When you must touch the body, edit through the editor UI (heading
dropdown, link button) rather than pasting large HTML blobs.

(Note: the corruption issue documented for Naver Blog's SmartEditor — pasted
UTF-8 mis-decoded as MacRoman → 외계어 — is a Naver-blog problem, not Tistory.
Tistory's TinyMCE handles paste fine, but minimal edits are still safer.)

## For sajangbu.com promo posts specifically

The goal is the post ranks for Coupang-seller / 정산 queries AND cleanly drives
to sajangbu.com:

- Title + lead paragraph target a real seller query (e.g. "쿠팡 정산 주기",
  "로켓그로스 수수료").
- At least one descriptive, contextual link to the relevant sajangbu.com page
  (anchor text = what the destination is about, not "여기" / "클릭").
- Tags overlap the sajangbu.com page's keywords so the two reinforce each other.
- Representative image set for the snippet thumbnail.

## Publish + submit

- Save/Update the post (confirm before clicking 발행/완료 — it's outward-facing).
- The new/updated URL is picked up via the blog's sitemap; to speed Naver, use
  웹페이지 수집 in Search Advisor on that URL, and Request Indexing in GSC.
