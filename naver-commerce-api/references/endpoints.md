# 네이버 커머스 API — 자주 쓰는 엔드포인트

Host: `https://api.commerce.naver.com`
모든 경로는 `scripts/ncommerce.py`로 호출. 인증 토큰·서명은 스크립트가 자동 처리.
공식 레퍼런스 인덱스: https://apicenter.commerce.naver.com/docs/commerce-api/current (정확한 파라미터·바디 스키마는 여기서 확인)

## 이 앱(온누리문방구, type=SELF)의 권한 현황 — 실측

| 그룹 | 경로 prefix | 상태 |
|---|---|---|
| 상품 | `/external/v1/products`, `/external/v2/products` | ✅ 호출 가능 (검증됨) |
| 주문(결제·배송) | `/external/v1/pay-order/seller/...` | ⚠️ GW.AUTHN — 앱에 "주문" API 사용권한 미부여 |
| 판매자 정보 | `/external/v1/seller/...` | ⚠️ GW.AUTHN — 권한 미부여 |

> ⚠️ GW.AUTHN("권한 없음")이 뜨면 토큰 문제가 아니라 **그 API 그룹이 앱에 허용 안 된 것**.
> 커머스API센터(어드민) → 애플리케이션 → API 사용 권한에서 해당 그룹을 추가 신청해야 열림. 사용자만 가능.
> GW.NOT_FOUND는 경로 자체가 틀린 것 — 위 레퍼런스 인덱스에서 정확한 경로 확인.

## 상품 (검증된 그룹)

**상품 목록 검색** — ✅ 검증됨
```
POST /external/v1/products/search
body: {"page":1,"size":50}            # searchKeyword, productStatusTypes 등 필터 가능
```
응답: `contents[].originProductNo`, `channelProducts[].channelProductNo`, 이름·재고·가격 등.
`originProductNo`(원상품)와 `channelProductNo`(채널상품)는 다름 — 수정 API는 보통 originProductNo 사용.

**상품 단건 조회**
```
GET /external/v2/products/origin-products/{originProductNo}
```

**상품 수정 (가격·재고·상품명·태그 등)** — ✅ 검증됨
```
PUT /external/v2/products/origin-products/{originProductNo}
body: 전체 상품 객체 (먼저 GET으로 받아 일부 필드만 바꿔 그대로 PUT)
```
- 상품명: `originProduct.name`. ⚠️ **함정**: 채널에 `smartstoreChannelProduct.channelProductName`이 설정돼 있으면 그게 실제 노출명을 덮어쓴다(검색·스토어 표시). 이 키가 있으면 origin.name만 바꿔선 노출명이 안 바뀌므로 `channelProductName`도 같이 수정할 것. (없으면 origin.name이 그대로 노출됨)
- SEO 태그: `originProduct.detailAttribute.seoInfo.sellerTags` = `[{"text":"키워드"}, ...]` (코드 없이 text만으로 등록 가능, 최대 10개)
- ⚠️ 태그 금지어: 제목/카테고리에 이미 있는 대표키워드(예: 러닝벨트, 힙색)나 일부 단어(예: 전자책)는 `Restricted.sellerTags`로 거부됨. 응답 메시지 `등록불가인 단어(A,B,C)`를 콤마 분리해 제거 후 재시도할 것. 태그는 제목과 겹치지 않는 보조·롱테일 키워드로 채우는 게 정석.

**상품 등록**
```
POST /external/v2/products
```

## 주문 (권한 부여 후 사용 가능, prefix 검증됨)

**변경된 주문 조회** (폴링용 — 마지막 조회 이후 상태 바뀐 주문 ID)
```
GET /external/v1/pay-order/seller/product-orders/last-changed-statuses
query: lastChangedFrom=2026-06-24T00:00:00.000+09:00   # ISO8601 +09:00
```

**주문 상세 조회**
```
POST /external/v1/pay-order/seller/product-orders/query
body: {"productOrderIds":["..."]}
```

> 발송처리·취소·교환·반품 등 액션 경로는 권한 부여 후 레퍼런스 인덱스에서 확인.

## 인증 (참고 — 스크립트가 자동 처리)

- Token URL: `POST https://api.commerce.naver.com/external/v1/oauth2/token`
- form body: `client_id`, `timestamp`(ms), `client_secret_sign`, `grant_type=client_credentials`, `type=SELF`
- 서명: `base64( bcrypt.hashpw("{client_id}_{timestamp}", client_secret) )`
  - bcrypt salt = client_secret 그 자체 (`$2a$04$...` 형식)
- 토큰 유효 ~3시간(10800s). 스크립트가 `~/.cache/naver-commerce/token.json`에 캐싱 + 만료/GW.AUTHN 시 자동 재발급.
- 인증 문서: https://apicenter.commerce.naver.com/docs/auth
