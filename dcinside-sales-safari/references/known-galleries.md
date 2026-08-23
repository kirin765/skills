# 검증된 dcinside 갤러리 카탈로그

2026-05-02~03 dcinside Sales Safari 작업에서 직접 프로빙·스크랩한 결과. 페르소나 명확하게 검증된 갤만 포함. 새 갤 발견 시 여기에 추가하라.

---

## 페르소나별 활성 갤

### 자영업·소상공인

| ID | 갤 종류 | 페르소나 | 12개월 메타 | 비고 |
|---|---|---|---|---|
| `sajang` | mgallery | 자영업 일반 사장 | 6,640 | 가장 큰 자영업 페르소나 갤 |
| `smallbusiness` | mgallery | 소상공인 일반 | 1,131 | sajang과 결 비슷, 보강용 |

### 이커머스 셀러

| ID | 갤 종류 | 페르소나 | 12개월 메타 | 비고 |
|---|---|---|---|---|
| `smartstore` | mgallery | 네이버/쿠팡 셀러 | 752 | 셀러 페인 메인 갤 |

### 학원·과외 강사

| ID | 갤 종류 | 페르소나 | 12개월 메타 | 비고 |
|---|---|---|---|---|
| `instructors` | mgallery | 학원강사 | 971 | 학원 운영 페르소나 검증됨 |
| `ptutor` | mgallery | 과외강사 | 624 | 김과외 분쟁 페인 압도적 |
| `slfnejdiif` | mgallery | 대치현강 | 미스캔 | 대치 현강 강사 niche |
| `spartasam` | mgallery | 스파르타샘 대치팀 | 미스캔 | 특정 강사팀 niche |

### 개발자

| ID | 갤 종류 | 페르소나 | 12개월 메타 | 비고 |
|---|---|---|---|---|
| `backend` | mgallery | 백엔드 개발자·취준생 | 32,449 | 매우 큼, 필터 강화 필요 |
| `vibecoding` | mgallery | 1인 LLM 빌더 | 154 | 작지만 페르소나 명확 |

### 직군 부분 검증·참고만

| ID | 갤 종류 | 페르소나 | 비고 |
|---|---|---|---|
| `daechi` | mgallery | 대치동 학군지 (강사·학부모·학생 혼재) | 후처리 필터 필요 |
| `1stfightingtutoring` | mgallery | 과외 niche | 페르소나 검증 더 필요 |

---

## 페이지1 row 활성도 기준

- 50: page 가득 참 (2024년 거의 매일 글 올라오는 활성갤)
- 30+: 활성, 12개월 1,000~10,000건 가능
- 10~30: 작은 niche 갤, 1,000건 미만 가능성
- <10: 죽은 갤, 12개월 100건 미만 — Sales Safari 부적합

---

## 갤 종류 (URL 경로 차이)

```
정식갤 (board):     https://gall.dcinside.com/board/lists/?id={ID}
마이너 (mgallery):  https://gall.dcinside.com/mgallery/board/lists/?id={ID}
미니 (mini):        https://gall.dcinside.com/mini/board/lists/?id={ID}
```

probe 시 세 경로 모두 시도해야 함 (probe_galleries.py가 자동 처리).

---

## 모바일 엔드포인트 (detail 수집용)

```
https://m.dcinside.com/board/{ID}/{post_num}
```

데스크탑 view 페이지는 댓글이 AJAX라서 별도 e_s_n_o CSRF 토큰 필요. 모바일은 단일 GET으로 본문+댓글 inline 반환 → 훨씬 쉬움. fetch_detail.py가 이걸 사용.

---

## 익명 작성자 dedup 키 (중요)

dcinside는 두 종류의 작성자:
- **유동(닉+IP)**: data-nick + data-ip 앞두 옥텟 (예: "자붕이 / 124.111")
- **고정ID(UID)**: data-uid (해시값)

dedup 키:
```
key = f"uid:{uid}" if uid else f"ip:{ip}/{nick}"
```

같은 IP 두 옥텟에서 같은 닉이면 동일인으로 가정 (소수 동명이인 가능하나 보수적 선택).
