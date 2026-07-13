# Coupang Open API — 자주 쓰는 엔드포인트

호스트: `https://api-gateway.coupang.com` · 업체코드(vendorId): `A01569984` (`{vendorId}`는 스크립트가 자동 치환)

모든 경로는 `/v2/providers/{provider}/apis/api/v{n}/...` — **항상 `apis`**(`apps` 아님). provider·버전만 계열마다 다름:
- 상품(seller_api): `/v2/providers/seller_api/apis/api/v1/marketplace/...`
- 그 외(openapi): `/v2/providers/openapi/apis/api/v{n}/vendors/{vendorId}/...` — 버전이 엔드포인트마다 다름

표기 `(실측✅)`은 이 머신(등록 IP)에서 라이브 200 확인. 그 외는 문서 기준이며, 쿠팡이 버전을 올리는 경우가 있으니 **쓰기 작업·로켓그로스는 호출 전 공식 문서로 재확인**한다.

## 상품 (seller_api/apis/api/v1)

| 작업 | 메서드 | 경로 |
|---|---|---|
| 상품 생성·등록 | POST | `/v2/providers/seller_api/apis/api/v1/marketplace/seller-products` |
| 상품 목록(페이징) | GET (실측✅) | `/v2/providers/seller_api/apis/api/v1/marketplace/seller-products?vendorId=A01569984&maxPerPage=50&nextToken=` (다음페이지는 응답의 `nextToken` 사용) |
| 상품 단건 조회 | GET | `/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{sellerProductId}` |
| 상품 수정 | PUT | `/v2/providers/seller_api/apis/api/v1/marketplace/seller-products` (전체 객체 PUT) |
| 상품 삭제 | DELETE | `/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{sellerProductId}` |
| 가격 변경 | PUT | `/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{vendorItemId}/prices/{price}` |
| 재고 변경 | PUT (실측✅) | `/v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/{vendorItemId}/quantities/{quantity}` (⚠️ `seller-products`가 아니라 `vendor-items` — `seller-products` 경로는 PRECONDITION_FAILED) |
| 판매 재개 / 중지 | PUT | `.../seller-products/{vendorItemId}/sales/resume` · `.../sales/stop` |
| 카테고리 추천 | POST | `/v2/providers/openapi/apis/api/v1/categorization/predict` (바디: 상품명 등) |
| 카테고리 메타 조회 | GET (실측✅) | `/v2/providers/seller_api/apis/api/v1/marketplace/meta/category-related-metas/display-category-codes/{code}` (provider는 `seller_api` — `openapi` 아님. 응답 `data.attributes[]`에 `inputType`(SELECT/INPUT)·`inputValues`·`required` 포함) |

상품 생성 바디는 필수 필드가 많다(displayCategoryCode, sellerProductName, vendorId, saleStartedAt/EndedAt, items[], 출고지/반품지 코드, 고시정보 등). 공식 "Product Creation" 문서의 스키마를 그대로 채운다.

## 주문 / 발주서 (openapi/apis/api/v4)

| 작업 | 메서드 | 경로 |
|---|---|---|
| 발주서 목록(기간) | GET (실측✅) | `/v2/providers/openapi/apis/api/v4/vendors/{vendorId}/ordersheets?createdAtFrom=2026-06-24T00:00&createdAtTo=2026-06-24T23:00&searchType=timeFrame&status=DELIVERING` |
| 발주서 단건(shipmentBoxId) | GET | `/v2/providers/openapi/apis/api/v4/vendors/{vendorId}/ordersheets/{shipmentBoxId}` |
| 발주서 단건(orderId) | GET | `/v2/providers/openapi/apis/api/v4/vendors/{vendorId}/{orderId}/ordersheets` |
| 상품준비중 처리(확인) | PUT | `/v2/providers/openapi/apis/api/v4/vendors/{vendorId}/ordersheets/acknowledgement` |
| 송장 업로드(배송) | POST | `/v2/providers/openapi/apis/api/v4/vendors/{vendorId}/orders/invoices` |
| 송장 수정 | PUT | `/v2/providers/openapi/apis/api/v4/vendors/{vendorId}/orders/invoices` |

`status`는 **필수**(생략 시 400 "required parameters are missing"). 값: ACCEPT(결제완료), INSTRUCT(상품준비중), DEPARTURE(배송지시), DELIVERING(배송중), FINAL_DELIVERY(배송완료). timeFrame 조회는 **`createdAtTo - createdAtFrom < 1일`** 이어야 한다(초과 시 400 "range should less than 1 day") — 기간이 길면 하루 단위로 쪼개고 상태별로 호출한다.

## 반품 / 교환 (openapi/apis)

| 작업 | 메서드 | 경로 |
|---|---|---|
| 반품 요청 목록 | GET | `/v2/providers/openapi/apis/api/v5/vendors/{vendorId}/returnRequests?createdAtFrom=&createdAtTo=&searchType=timeFrame&status=` |
| 반품 승인 | PUT | `/v2/providers/openapi/apis/api/v5/vendors/{vendorId}/returnRequests/{receiptId}/approval` |
| 교환 요청 목록 | GET | `/v2/providers/openapi/apis/api/v4/vendors/{vendorId}/exchangeRequests?...` |

## 출고지 / 반품지 (openapi/apis)

| 작업 | 메서드 | 경로 |
|---|---|---|
| 출고지 목록 조회 | POST (실측✅) | `/v2/providers/openapi/apis/api/v5/vendors/{vendorId}/outboundShippingCenters` (바디로 검색조건; GET 아님) |
| 반품지 목록 조회 | GET (실측✅) | `/v2/providers/openapi/apis/api/v4/vendors/{vendorId}/returnShippingCenters?pageNum=1&pageSize=50` |

## 정산 / 매출 (openapi/apis/api/v1)

| 작업 | 메서드 | 경로 |
|---|---|---|
| 매출 내역 | GET | `/v2/providers/openapi/apis/api/v1/revenue-history?vendorId=A01569984&recognitionDateFrom=&recognitionDateTo=&maxPerPage=` |
| 지급 내역(정산) | GET | `/v2/providers/openapi/apis/api/v1/settlement-histories?vendorId=A01569984&revenueRecognitionYearMonth=YYYY-MM` |

## 로켓그로스 (RFM) — ⚠️ 별도 확인 필요

스크린샷에 있던 "로켓그로스 상품 생성 API"는 마켓플레이스 상품 생성과 플로우·필수 필드(입고/물류 관련)가 다르다. 정확한 경로·바디는 공식 로켓그로스(제트배송/RFM) 문서로 확인한 뒤 호출한다. 여기 마켓플레이스 경로를 그대로 쓰지 말 것.

## 진단 단서

| 응답 | 의미 | 조치 |
|---|---|---|
| `403 FORBIDDEN ... ip address ... not allowed` | IP 미허용 | Wing 연동정보에 호출 IP 추가 또는 등록 서버에서 실행 |
| `Provider id is not specified correctly.` | 경로 접두사/세그먼트 오류 | `apps`↔`apis`, 버전 번호 재확인 |
| `PRECONDITION_FAILED ... did you mean ... POST?` | 메서드 불일치 | 해당 엔드포인트의 올바른 메서드로 |
| 깨진 바이너리 출력 | gzip 응답 | 스크립트가 자동 해제함(구버전이면 최신 `coupang.py` 사용) |
