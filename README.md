# 송파구 토지이용 분석 웹앱

React + Vite + deck.gl + MapLibre 기반의 송파구 토지이용 분석 대시보드다.  
건축물 기준과 필지 기준 집계를 모두 지원하고, 필지 대표 용도는 건축물 용도, 지목, 도시계획 시설, 근접 건축물 보조 규칙을 함께 사용해 만든다.

## 실행 주의

`index.html`을 브라우저에서 직접 열지 않는다.

이 프로젝트는 Vite 개발 서버로 실행해야 한다. `file://` 방식으로 열면 브라우저 CORS 정책 때문에 `/src/main.jsx` 같은 모듈 파일을 읽지 못해 흰 화면이 나온다.

## 설치 및 실행

```bash
npm install
npm run dev
```

접속 주소:

- [http://localhost:5173/](http://localhost:5173/)

PowerShell에서 `npm` 실행이 막히면 아래 명령을 사용한다.

```bash
npm.cmd install
npm.cmd run dev
```

## 빌드 확인

```bash
npm run build
npm run preview
```

## 데이터 전처리

### 1. 건축물 전처리

입력 파일:

- `data/raw/buildings.shp`
- `data/raw/songpa_boundary.geojson`

실행:

```bash
pip install geopandas pandas pyogrio shapely
python scripts/preprocess_landuse.py
```

출력:

- `public/data/buildings_songpa.geojson`
- `public/data/landuse_summary.csv`

### 2. 송파구 경계 전처리

입력 파일:

- `data/raw/sigungu_boundary.shp`

실행:

```bash
python scripts/preprocess_boundary.py
```

출력:

- `public/data/songpa_boundary.geojson`

### 3. 필지 기반 토지이용 전처리

입력 파일:

- `data/raw/parcels.shp`
- `public/data/buildings_songpa.geojson`
- `public/data/songpa_boundary.geojson`
- 선택: `data/raw/urban_facilities` 또는 `data/raw/inspect/urban_facilities_seoul` 아래 도시계획 시설 SHP

실행:

```bash
python scripts/preprocess_parcels.py
python scripts/diagnose_unclassified.py
```

출력:

- `public/data/parcels_songpa.geojson`
- `public/data/parcels_landuse_summary.csv`
- `public/data/classification_diagnosis.csv`
- `public/data/unclassified_diagnosis.csv`
- `public/data/urban_facilities_songpa.geojson`

## 현재 분류 규칙

필지 대표 용도 우선순위:

1. 건축물 용도 기준
2. 지목 기준
3. 도시계획 시설 기준
4. 용도지역 보조 기준
5. 근접 건축물 보조 매칭
6. 건물없음
7. 미분류

중요:

- 공원, 하천, 도로 같은 비건축 공간도 공적 속성값이 있을 때만 분류한다.
- 미분류는 건축물, 지목, 도시계획 시설, 용도지역 정보만으로 대표 용도를 판단하기 어려운 필지다.
- 법적 판단이 필요한 경우에는 원천 공간정보와 건축물대장, 지목, 도시계획 도면을 함께 확인해야 한다.

## 주요 기능

- 필지 기준 / 건물 기준 집계 전환
- 통계 계산 옵션 전환
- 배경지도 선택
- 송파구 경계 표시
- 건물 보조 레이어 ON/OFF
- 필지 클릭 팝업과 건물 클릭 팝업
- 토지이용 색상 투명도 슬라이더
- 토지이용 구성비 도넛 차트
- 보고서 모달과 CSV 다운로드
- 데이터가 없을 때 fallback UI

## 데이터 경로

앱은 아래 파일이 있으면 우선 로딩한다.

- `public/data/songpa_boundary.geojson`
- `public/data/buildings_songpa.geojson`
- `public/data/landuse_summary.csv`
- `public/data/parcels_songpa.geojson`
- `public/data/parcels_landuse_summary.csv`
- `public/data/classification_diagnosis.csv`
- `public/data/unclassified_diagnosis.csv`
- `public/data/urban_facilities_songpa.geojson`

