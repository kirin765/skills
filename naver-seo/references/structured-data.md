# Naver structured data (구조화된 데이터)

Naver reads schema.org structured data to enrich results. Use **JSON-LD** (Naver's
recommended format alongside Microdata) in a `<script type="application/ld+json">` in
`<head>` or body.

## Support matrix — what Naver actually documents

Naver's 웹마스터 가이드 documents these rich types (one page each under
`structured-data-*`):

| Type | schema.org `@type` | Good for |
|------|--------------------|----------|
| 게시글 | `Article` / `NewsArticle` / `BlogPosting` | blog, news, content |
| 빵부스러기 | `BreadcrumbList` | every multi-level site (nav path in SERP) |
| FAQ | `FAQPage` | help/policy pages, product Q&A |
| 평점/리뷰 | `AggregateRating`, `Review` | products, places, services |
| 레시피 | `Recipe` | cooking content |
| 방법 | `HowTo` | tutorials |
| 동영상 | `VideoObject` | video pages |
| 영화/TV | `Movie`, `TVSeries` | media |
| 음식점/주소 | `Restaurant`, `PostalAddress` | local business |
| 소프트웨어 | `SoftwareApplication` | apps |
| 채용 | `JobPosting` | job listings |
| 채널 | site channel | linking your Naver channels |
| 캐러셀 | `ItemList` | carousels of the above |

**Key gap vs Google:** `Product` is **not** a documented Naver rich type. Ship Product
JSON-LD anyway (it's valid schema.org and Google uses it), but for Naver SERP enrichment
on a shop, the leverage is **BreadcrumbList + FAQPage + AggregateRating/Review**, plus an
`Organization`/`Store` block for brand identity.

## Rules

- Use `@type` and properties exactly as schema.org defines them. A page can carry
  multiple types.
- Structured data must reflect content **visible on the page** — don't mark up ratings
  or FAQs that users can't see (cloaking → penalty).
- Validate with a public tool (Google Rich Results Test / schema.org validator) before
  shipping; Naver accepts standard schema.org.

## Copy-paste JSON-LD

### Organization / Store (sitewide — put in the root layout)

```json
{
  "@context": "https://schema.org",
  "@type": "Store",
  "name": "브랜드명",
  "url": "https://www.example.com",
  "logo": "https://www.example.com/logo.png",
  "image": "https://www.example.com/og.jpg",
  "telephone": "+82-10-0000-0000",
  "email": "help@example.com",
  "address": {
    "@type": "PostalAddress",
    "addressCountry": "KR",
    "addressRegion": "경기도",
    "addressLocality": "광명시",
    "streetAddress": "소하로 56"
  }
}
```

### BreadcrumbList (per page)

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {"@type": "ListItem", "position": 1, "name": "홈", "item": "https://www.example.com"},
    {"@type": "ListItem", "position": 2, "name": "카테고리", "item": "https://www.example.com/category"},
    {"@type": "ListItem", "position": 3, "name": "상품명", "item": "https://www.example.com/products/1"}
  ]
}
```

### FAQPage (policy / help / product Q&A)

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "배송은 얼마나 걸리나요?",
      "acceptedAnswer": {"@type": "Answer", "text": "결제 확인 후 평균 2~3 영업일 이내 출고됩니다."}
    },
    {
      "@type": "Question",
      "name": "교환·환불이 가능한가요?",
      "acceptedAnswer": {"@type": "Answer", "text": "상품 수령 후 7일 이내 신청 가능합니다."}
    }
  ]
}
```

### Product (for Google; harmless on Naver)

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "상품명",
  "image": "https://www.example.com/products/1.jpg",
  "description": "상품 설명",
  "brand": {"@type": "Brand", "name": "브랜드명"},
  "sku": "SKU-001",
  "offers": {
    "@type": "Offer",
    "url": "https://www.example.com/products/1",
    "price": "10000",
    "priceCurrency": "KRW",
    "availability": "https://schema.org/InStock",
    "itemCondition": "https://schema.org/NewCondition"
  }
}
```
