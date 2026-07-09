# 토스쇼핑 Open API 엔드포인트

모든 경로의 베이스 호스트는 `https://shopping-fep.toss.im` (테스트: `https://shopping-fep-alpha.toss.im`).
스크립트에는 `/api/v3/shopping-fep/...` 부터의 경로만 넘긴다 (호스트는 스크립트가 붙임).

- `*` 표시된 파라미터는 필수.
- `partnerName` 은 거의 모든 조회에 있는 선택 파라미터(파트너 필터). 보통 생략 가능.
- 커서 페이지네이션: 응답의 `nextToken`/`nextCursor` 를 다음 요청 쿼리로 넘겨 반복.
- 바디 스키마가 복잡한 쓰기 엔드포인트(상품 등록 등)는 공식 문서에서 필드를 확인:
  https://shopping-docs.toss.im/dev — 상품 등록 상세: `/dev/api-1/register-product`

## 목차
- [카테고리·고시](#카테고리고시)
- [상품](#상품)
- [상품 옵션·가격·재고](#상품-옵션가격재고)
- [주문](#주문)
- [배송](#배송)
- [클레임(취소·반품·교환)](#클레임취소반품교환)
- [가맹점(셀러 정보·페널티·휴무·배송지)](#가맹점)
- [정산](#정산)

## 카테고리·고시
| Method | Path | 설명 | 파라미터 |
|---|---|---|---|
| GET | `/api/v3/shopping-fep/products/categories/children` | 카테고리 항목 조회(자식 카테고리) | id, partnerName |
| GET | `/api/v3/shopping-fep/category/{categoryId}/constraint-templates` | 상품 제약 조건 템플릿 조회 | categoryId* |
| GET | `/api/v3/shopping-fep/notices/category-codes` | 정보제공 고시 카테고리 목록 | partnerName |
| GET | `/api/v3/shopping-fep/notices` | 정보제공 고시 항목 조회 | categoryCode* |

## 상품
| Method | Path | 설명 | 파라미터 |
|---|---|---|---|
| GET | `/api/v3/shopping-fep/products/v2` | 상품 목록 조회 | regStartDate, regEndDate, productIds, nextToken, size |
| GET | `/api/v3/shopping-fep/products/{productId}/v2` | 상품 단건 조회 | productId* |
| POST | `/api/v3/shopping-fep/products/v2` | 상품 등록 | body (register-product 문서 참고) |
| PUT | `/api/v3/shopping-fep/products/{productId}/v2` | 상품 정보 변경 | productId*, body |
| POST | `/api/v3/shopping-fep/products/remove` | 상품 삭제 | body(productIds) |
| POST | `/api/v3/shopping-fep/products/show` | 노출 상태 보이기 | body |
| POST | `/api/v3/shopping-fep/products/hide` | 노출 상태 숨기기 | body |
| GET | `/api/v3/shopping-fep/product-constraint-templates/{templateId}` | 제약 템플릿 상세 | templateId* |
| POST | `/api/v3/shopping-fep/purchase-limits` | 구매 개수 제한 생성 | body |
| GET | `/api/v3/shopping-fep/purchase-limits/product-ids/{productId}` | 구매 개수 제한 조회 | productId* |
| DELETE | `/api/v3/shopping-fep/purchase-limits` | 구매 개수 제한 제거 | body |

## 상품 옵션·가격·재고
| Method | Path | 설명 | 파라미터 |
|---|---|---|---|
| GET | `/api/v3/shopping-fep/product-items/grouped-by-products` | 옵션 그룹 검색(커서, product 단위) | nextCursor, prevCursor, pageSize, itemStatuses, productName, productIds, itemIds |
| GET | `/api/v3/shopping-fep/products/{productId}/product-items` | 단일 상품 아이템 목록(커서) | productId*, cursorItemId, pageSize, itemStatuses, itemIds |
| PUT | `/api/v3/shopping-fep/product-items/{productItemId}/sale-price` | 옵션 판매가 수정 | productItemId*, body |
| PUT | `/api/v3/shopping-fep/product-items/{productItemId}/origin-price` | 옵션 정상가 수정 | productItemId*, body |
| PUT | `/api/v3/shopping-fep/product-items/{productItemId}/stocks/normal-stock/remaining-count` | 정상 재고 수량 변경 | productItemId*, body |

## 주문
| Method | Path | 설명 | 파라미터 |
|---|---|---|---|
| GET | `/api/v3/shopping-fep/orders/v2` | 주문 내역 조회 | status, startDate*, endDate*, nextCursor, limit |
| GET | `/api/v3/shopping-fep/orders/products/{orderProductId}` | 주문 상품 단건 조회 | orderProductId* |
| PUT | `/api/v3/shopping-fep/orders/products/status` | 주문 상품 상태 변경 | body (status=DELAY_SHIPPING 이면 shippingDeadlineAt 필수) |

## 배송
| Method | Path | 설명 | 파라미터 |
|---|---|---|---|
| GET | `/api/v3/shopping-fep/orders/delivery-companies` | 택배사 정보 조회 | partnerName |
| GET | `/api/v3/shopping-fep/delivery-companies` | 택배사 목록 조회 | — |
| PUT | `/api/v3/shopping-fep/orders/products/delivery` | 주문 상품 배송정보(송장) 변경 | body |
| GET | `/api/v3/shopping-fep/merchants/group-delivery/delivery-location/v2` | 배송비 묶음 그룹 조회 | nextToken, size |
| POST | `/api/v3/shopping-fep/merchants/group-delivery/delivery-location` | 배송비 묶음 그룹 등록 | body |
| PUT | `/api/v3/shopping-fep/merchants/group-delivery/delivery-location` | 배송비 묶음 그룹 수정 | body |
| GET | `/api/v3/shopping-fep/merchants/group-delivery/exchange-refund-location/v2` | 교환/반품지 조회 | nextToken, size |
| POST | `/api/v3/shopping-fep/merchants/group-delivery/exchange-refund-location` | 교환/반품지 등록 | body |
| PUT | `/api/v3/shopping-fep/merchants/group-delivery/exchange-refund-location` | 교환/반품지 수정 | body |

## 클레임(취소·반품·교환)
| Method | Path | 설명 | 파라미터 |
|---|---|---|---|
| GET | `/api/v3/shopping-fep/claims` | 클레임 목록 조회 | type, status, fromRequestDate, toRequestDate, orderIds, nextToken, size |
| POST | `/api/v3/shopping-fep/order-products/{orderProductId}/seller-cancel` | 판매자 주문 취소 | orderProductId*, body |
| POST | `/api/v3/shopping-fep/claims/{claimId}/cancel/approval` | 취소 요청 승인 | claimId* |
| POST | `/api/v3/shopping-fep/claims/{claimId}/cancel/rejection` | 취소 요청 거절 | claimId*, body |
| POST | `/api/v3/shopping-fep/claims/{claimId}/return/approval` | 반품 요청 승인 | claimId* |
| POST | `/api/v3/shopping-fep/claims/{claimId}/return/rejection` | 반품 요청 거절 | claimId*, body |
| POST | `/api/v3/shopping-fep/claims/{claimId}/return/collection` | 반품 수거 완료 | claimId* |
| POST | `/api/v3/shopping-fep/claims/{claimId}/return/collection-rejection` | 반품 반려 | claimId*, body |
| POST | `/api/v3/shopping-fep/claims/{claimId}/return/completion` | 반품 완료 | claimId* |
| POST | `/api/v3/shopping-fep/claims/{claimId}/exchange/approval` | 교환 요청 승인 | claimId* |
| POST | `/api/v3/shopping-fep/claims/{claimId}/exchange/rejection` | 교환 요청 거절 | claimId*, body |
| POST | `/api/v3/shopping-fep/claims/{claimId}/exchange/collection` | 교환 수거 완료 | claimId* |
| POST | `/api/v3/shopping-fep/claims/{claimId}/exchange/collection-rejection` | 교환 반려 | claimId*, body |
| POST | `/api/v3/shopping-fep/claims/{claimId}/exchange/delivery` | 교환 재배송 | claimId*, body |
| POST | `/api/v3/shopping-fep/claims/{claimId}/exchange/completion` | 교환 완료 | claimId* |

클레임 `type`: `CANCEL`(취소), `RETURN`(반품), `EXCHANGE`(교환).

## 가맹점
| Method | Path | 설명 | 파라미터 |
|---|---|---|---|
| GET | `/api/v3/shopping-fep/merchants/penalty/summary` | 셀러 페널티 요약 | partnerName |
| GET | `/api/v3/shopping-fep/merchants/penalty/impositions` | 페널티 부과 목록 | cursorId, size |
| POST | `/api/v3/shopping-fep/merchants/penalty/appeals` | 페널티 소명 자료 제출 | penaltyImpositionId*, description*, body |
| GET | `/api/v3/shopping-fep/merchants/holidays` | 휴무일 목록 조회 | startDate*, endDate* |
| POST | `/api/v3/shopping-fep/merchants/holidays` | 휴무일 등록 | body |
| PUT | `/api/v3/shopping-fep/merchants/holidays/{holidayId}` | 휴무일 수정 | holidayId*, body |
| DELETE | `/api/v3/shopping-fep/merchants/holidays/{holidayId}` | 휴무일 삭제 | holidayId* |

## 정산
| Method | Path | 설명 | 파라미터 |
|---|---|---|---|
| GET | `/api/v3/shopping-fep/settlement-steps` | 정산 건별 목록 조회 | dateCondition*, fromDate*, toDate*, size*, nextToken |

## 참고
- 요청 한도: 쓰기 초당 30회, 읽기 초당 50회. 초과 시 `TOO_MANY_REQUEST`.
- 응답 필드·에러 코드는 예고 없이 변경될 수 있음. 여기 없거나 바디 스키마가 불확실하면
  각 페이지의 `.md` 를 조회한다 (예: `curl -sL https://shopping-docs.toss.im/dev/api-2/product.md`).
  각 페이지에는 전체 OpenAPI 스펙(JSON)이 들어있다.
