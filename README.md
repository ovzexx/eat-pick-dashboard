# EAT-PICK 영양 랭킹

식품의약품안전처 음식·가공식품 공공데이터를 기반으로 칼로리·단백질·당류를 100g 동일 기준으로 비교하는 웹 대시보드입니다.

**라이브 데모**: https://eat-pick-dashboard.vercel.app

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 영양 랭킹 | 저칼로리 / 고단백 / 저당류 순 정렬 |
| 검색 자동완성 | 식품명 입력 시 드롭다운 추천 |
| 필터 | 대·중분류, 칼로리·단백질·당류 범위 |
| 즐겨찾기 | ★ 버튼으로 저장, 즐겨찾기 전용 뷰 (로컬스토리지) |
| 비교 차트 | 최대 4개 식품을 막대 / 레이더 차트로 비교 |
| 링크 공유 | 현재 검색 조건을 URL로 공유 |

**비교 기준**: 원본의 `영양성분함량기준량`이 g 단위로 명시된 항목만 100g 기준으로 환산합니다. ml·1회 제공량 등 무게 환산이 불가능한 항목은 제외합니다.

---

## 기술 스택

- **프론트엔드**: React 18 · TypeScript · Vite · Recharts
- **백엔드**: FastAPI (Python) · SQLite
- **데이터**: 식품의약품안전처 공공데이터 (31만+ 건, Git LFS)

---

## 로컬 실행

Git LFS가 설치되어 있어야 원본 Excel 파일을 받을 수 있습니다.

```bash
git lfs install
git clone https://github.com/ovzexx/eat-pick-dashboard.git
cd eat-pick-dashboard
./start.sh
```

처음 실행 시 패키지 설치와 데이터 변환(약 31만 건)이 수행되므로 몇 분 소요될 수 있습니다. 준비되면 브라우저에서 http://127.0.0.1:5173 을 열어주세요.

종료: 터미널에서 `Ctrl+C`

---

## 배포 구조

```
프론트엔드  →  Vercel  (정적 빌드)
백엔드      →  Railway (FastAPI + SQLite)
```

### Vercel (프론트엔드)

```bash
vercel --prod
```

`VITE_API_BASE` 환경변수에 Railway 백엔드 URL을 설정해야 합니다.

### Railway (백엔드)

GitHub 저장소를 Railway에 연결하면 `build.sh`가 자동 실행됩니다.

- 빌드: Excel → SQLite 변환 (5~10분 소요)
- 시작: `uvicorn` FastAPI 서버

Railway 환경변수:
```
ALLOWED_ORIGINS=https://eat-pick-dashboard.vercel.app
```

---

## 데이터 갱신

새 Excel 파일로 DB를 재생성하려면 `data/foods.db`를 삭제한 뒤 `./setup.sh`를 실행합니다.
