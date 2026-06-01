from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon


ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_PARCELS = ROOT_DIR / "data" / "raw" / "parcels.shp"
INPUT_BUILDINGS = ROOT_DIR / "public" / "data" / "buildings_songpa.geojson"
INPUT_BOUNDARY = ROOT_DIR / "public" / "data" / "songpa_boundary.geojson"
URBAN_FACILITY_DIR_CANDIDATES = [
    ROOT_DIR / "data" / "raw" / "urban_facilities",
    ROOT_DIR / "data" / "raw" / "inspect" / "urban_facilities_seoul",
    ROOT_DIR.parent / "data" / "raw" / "inspect" / "urban_facilities_seoul",
    ROOT_DIR.parent / "data" / "raw" / "urban_facilities",
]
OUTPUT_DIR = ROOT_DIR / "public" / "data"
OUTPUT_PARCELS = OUTPUT_DIR / "parcels_songpa.geojson"
OUTPUT_SUMMARY = OUTPUT_DIR / "parcels_landuse_summary.csv"
OUTPUT_DIAGNOSIS = OUTPUT_DIR / "classification_diagnosis.csv"
OUTPUT_UNCLASSIFIED = OUTPUT_DIR / "unclassified_diagnosis.csv"
OUTPUT_URBAN_FACILITIES = OUTPUT_DIR / "urban_facilities_songpa.geojson"
TARGET_CRS = "EPSG:5179"
WEB_CRS = "EPSG:4326"
NEAR_DISTANCE_M = 2.0

PARCEL_ID_CANDIDATES = [
    "pnu",
    "PNU",
    "필지고유번호",
    "고유번호",
    "A1",
    "JIBUN",
    "jibun",
]

LAND_CATEGORY_CANDIDATES = [
    "JIMOK",
    "jimok",
    "지목",
    "지목명",
    "LND_CGR",
    "LND_CGR_NM",
    "land_category",
    "jimok_nm",
    "JIMOK_NM",
]

SONGPA_CODE = "11710"

BUILDING_RULES = [
    (["단독주택", "다가구", "다중주택", "공관"], "단독주택"),
    (["아파트", "연립주택", "다세대주택", "공동주택"], "공동주택"),
    (["제1종근린생활시설", "제2종근린생활시설", "근린생활"], "근린생활시설"),
    (["판매시설", "도매시장", "소매시장", "백화점", "상점"], "판매시설"),
    (["교육연구시설", "학교", "교육", "연구", "도서관"], "교육연구시설"),
    (["의료시설", "병원", "의원", "종합병원", "요양병원"], "의료/노유자시설"),
    (["노유자시설", "아동복지시설", "사회복지시설", "어린이집"], "의료/노유자시설"),
    (["운동시설", "체육", "체육관", "골프연습장"], "운동시설"),
    (["업무시설", "공공업무시설", "오피스텔", "사무소"], "업무시설"),
    (["숙박시설", "호텔", "여관"], "숙박시설"),
    (["위락시설", "유흥주점", "단란주점"], "위락시설"),
    (["문화및집회시설", "공연장", "전시장", "집회장"], "문화및집회시설"),
    (["종교시설", "교회", "성당", "사찰"], "종교시설"),
    (["공장"], "공장"),
    (["창고시설"], "창고시설"),
    (["자동차관련시설", "주차장", "정비공장"], "자동차관련시설"),
    (["방송통신시설"], "방송통신시설"),
    (["발전시설"], "발전시설"),
    (["관광휴게시설"], "관광휴게시설"),
    (["묘지관련시설"], "묘지관련시설"),
]

JIMOK_RULES = [
    (["공장용지"], "공장"),
    (["학교용지"], "교육연구시설"),
    (["주차장"], "자동차관련시설"),
    (["창고용지"], "창고시설"),
    (["종교용지"], "종교시설"),
    (["체육용지"], "운동시설"),
    (["공원", "유원지", "임야"], "공원/녹지"),
    (["도로", "철도용지"], "도로/교통시설"),
    (["하천", "구거", "유지", "제방"], "하천/수공간"),
    (["유원지"], "관광휴게시설"),
]

URBAN_FACILITY_RULES = [
    (["공원", "녹지", "광장"], "공원/녹지"),
    (["도로", "차고지", "주차장", "철도", "역사"], "도로/교통시설"),
    (["학교"], "교육연구시설"),
    (["공공청사", "파출소"], "업무시설"),
    (["하천"], "하천/수공간"),
    (["운동장", "체육"], "운동시설"),
    (["문화"], "문화및집회시설"),
    (["사회복지", "복지", "어린이집"], "의료/노유자시설"),
    (["의료"], "의료/노유자시설"),
]


def main() -> int:
    try:
        print_header("송파구 필지 기반 토지이용 전처리 시작")
        validate_input_paths()

        parcels = read_spatial_file(INPUT_PARCELS, "필지 원본")
        buildings = read_spatial_file(INPUT_BUILDINGS, "건물 분석 결과")
        boundary = read_spatial_file(INPUT_BOUNDARY, "송파구 경계")
        facilities = read_urban_facilities()

        parcels = ensure_crs(parcels, "필지 원본")
        buildings = ensure_crs(buildings, "건물 분석 결과")
        boundary = ensure_crs(boundary, "송파구 경계")
        facilities = ensure_crs(facilities, "도시계획 시설") if facilities is not None else None

        parcels_5179 = clean_geometries(parcels.to_crs(TARGET_CRS), "필지 원본")
        buildings_5179 = clean_geometries(buildings.to_crs(TARGET_CRS), "건물 분석 결과")
        boundary_5179 = clean_geometries(boundary.to_crs(TARGET_CRS), "송파구 경계")
        facilities_5179 = (
            clean_geometries(facilities.to_crs(TARGET_CRS), "도시계획 시설")
            if facilities is not None
            else None
        )

        clipped_parcels = clip_to_songpa(parcels_5179, boundary_5179, "필지")
        if clipped_parcels.empty:
            raise ValueError("송파구 경계로 clip한 뒤 남은 필지가 없습니다.")

        parcel_id_column = find_column(clipped_parcels, PARCEL_ID_CANDIDATES, "필지 고유번호", required=False)
        land_category_column = find_column(clipped_parcels, LAND_CATEGORY_CANDIDATES, "지목", required=False)

        parcels_work = clipped_parcels.copy()
        parcels_work["parcel_id"] = build_ids(parcels_work, parcel_id_column, prefix="PCL")
        parcels_work["id"] = parcels_work["parcel_id"]
        parcels_work["area_m2"] = parcels_work.geometry.area.round(1)
        parcels_work["jimok"] = (
            parcels_work[land_category_column].fillna("").astype(str).str.strip()
            if land_category_column
            else ""
        )

        buildings_work = prepare_buildings(buildings_5179)
        facilities_work = prepare_urban_facilities(facilities_5179, boundary_5179) if facilities_5179 is not None else None

        classified = classify_parcels(parcels_work, buildings_work, facilities_work)
        summary = create_summary(classified)
        diagnosis = create_diagnosis(classified)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        save_geojson(classified, OUTPUT_PARCELS)
        summary.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
        diagnosis.to_csv(OUTPUT_DIAGNOSIS, index=False, encoding="utf-8-sig")
        diagnosis.to_csv(OUTPUT_UNCLASSIFIED, index=False, encoding="utf-8-sig")
        if facilities_work is not None and not facilities_work.empty:
            save_geojson(facilities_work, OUTPUT_URBAN_FACILITIES)

        print_results(classified, summary, diagnosis)
        print_header("필지 전처리 완료")
        print(f"- GeoJSON 저장: {OUTPUT_PARCELS}")
        print(f"- 요약 CSV 저장: {OUTPUT_SUMMARY}")
        print(f"- 진단 CSV 저장: {OUTPUT_DIAGNOSIS}")
        if facilities_work is not None and not facilities_work.empty:
            print(f"- 시설 GeoJSON 저장: {OUTPUT_URBAN_FACILITIES}")
        return 0
    except Exception as error:
        print("\n[오류] 필지 전처리 중 문제가 발생했습니다.", file=sys.stderr)
        print(f"- 원인: {error}", file=sys.stderr)
        print(
            "- 확인 사항: parcels.shp, buildings_songpa.geojson, songpa_boundary.geojson, 도시계획 시설 SHP 구조를 점검해주세요.",
            file=sys.stderr,
        )
        return 1


def validate_input_paths() -> None:
    missing = [str(path) for path in (INPUT_PARCELS, INPUT_BUILDINGS, INPUT_BOUNDARY) if not path.exists()]
    if missing:
        raise FileNotFoundError("필수 입력 파일을 찾지 못했습니다.\n" + "\n".join(f"- {path}" for path in missing))


def read_spatial_file(path: Path, label: str) -> gpd.GeoDataFrame:
    errors: list[str] = []
    for encoding in ("cp949", "utf-8"):
        try:
            print(f"\n[{label}] 읽는 중... encoding={encoding}")
            dataframe = gpd.read_file(path, engine="pyogrio", encoding=encoding)
            print(f"- 성공: {len(dataframe):,}건, CRS={dataframe.crs}")
            print(f"- 컬럼 목록: {list(dataframe.columns)}")
            return dataframe
        except Exception as error:
            errors.append(f"encoding={encoding}: {error}")
    raise RuntimeError(
        f"{label} 파일을 읽지 못했습니다.\n- 경로: {path}\n"
        + "\n".join(f"- 시도 실패: {message}" for message in errors)
    )


def read_urban_facilities() -> gpd.GeoDataFrame | None:
    facility_files: list[Path] = []
    for directory in URBAN_FACILITY_DIR_CANDIDATES:
        if directory.exists():
            facility_files.extend(sorted(directory.glob("UPIS_C_UQ*.shp")))
    if not facility_files:
        print("\n[도시계획 시설] 시설 SHP를 찾지 못해 이 단계는 건너뜁니다.")
        return None

    frames = []
    for shp in facility_files:
        gdf = read_spatial_file(shp, f"도시계획 시설 {shp.name}")
        mask = build_songpa_mask(gdf)
        subset = gdf.loc[mask].copy() if mask is not None else gdf.copy()
        if subset.empty:
            continue
        subset["facility_layer"] = shp.stem
        frames.append(subset)

    if not frames:
        print("\n[도시계획 시설] 송파구 관련 시설이 없어 이 단계는 건너뜁니다.")
        return None

    merged = pd.concat(frames, ignore_index=True)
    facility_gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs=frames[0].crs)
    print(f"\n[도시계획 시설] 송파구 후보 {len(facility_gdf):,}건을 수집했습니다.")
    return facility_gdf


def build_songpa_mask(dataframe: gpd.GeoDataFrame) -> pd.Series | None:
    candidate_columns = [column for column in ["SIGNGU_SE", "PRESENT_SN", "WTNNC_SN", "NTFC_SN"] if column in dataframe.columns]
    mask = None
    for column in candidate_columns:
        column_mask = dataframe[column].astype(str).str.contains(SONGPA_CODE, na=False)
        mask = column_mask if mask is None else (mask | column_mask)
    return mask


def ensure_crs(dataframe: gpd.GeoDataFrame, label: str) -> gpd.GeoDataFrame:
    if dataframe.crs is None:
        raise ValueError(f"{label} 데이터에 CRS 정보가 없습니다. 원본 좌표계(.prj)를 확인해주세요.")
    return dataframe


def clean_geometries(dataframe: gpd.GeoDataFrame, label: str) -> gpd.GeoDataFrame:
    cleaned = dataframe.copy()
    before_count = len(cleaned)
    cleaned = cleaned[~cleaned.geometry.isna()].copy()
    cleaned = cleaned[~cleaned.geometry.is_empty].copy()
    cleaned["geometry"] = cleaned.geometry.buffer(0)
    cleaned["geometry"] = cleaned.geometry.apply(extract_polygonal_geometry)
    cleaned = cleaned[~cleaned.geometry.isna()].copy()
    cleaned = cleaned[~cleaned.geometry.is_empty].copy()
    cleaned = cleaned[cleaned.geometry.is_valid].copy()
    print(f"- {label} geometry 정리: {len(cleaned):,}건 유지, {before_count - len(cleaned):,}건 제거")
    return cleaned


def extract_polygonal_geometry(geometry):
    if geometry is None or geometry.is_empty:
        return None
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry
    if isinstance(geometry, GeometryCollection):
        polygon_parts = [geom for geom in geometry.geoms if isinstance(geom, (Polygon, MultiPolygon))]
        if not polygon_parts:
            return None
        flattened: list[Polygon] = []
        for part in polygon_parts:
            if isinstance(part, Polygon):
                flattened.append(part)
            else:
                flattened.extend(list(part.geoms))
        return MultiPolygon(flattened) if len(flattened) > 1 else flattened[0]
    return None


def clip_to_songpa(dataframe: gpd.GeoDataFrame, boundary: gpd.GeoDataFrame, label: str) -> gpd.GeoDataFrame:
    print(f"\n[공간 클립] 송파구 경계로 {label}를 자릅니다.")
    clipped = gpd.clip(dataframe, boundary)
    clipped = clean_geometries(clipped, f"{label} clip 결과")
    print(f"- {label} 남은 개수: {len(clipped):,}건")
    return clipped


def find_column(dataframe: pd.DataFrame, candidates: list[str], label: str, required: bool = True) -> str | None:
    columns = list(dataframe.columns)
    for candidate in candidates:
        if candidate in columns:
            print(f"- {label} 컬럼 선택: {candidate}")
            return candidate
    if required:
        raise ValueError(f"{label} 컬럼을 찾지 못했습니다. 현재 컬럼: {columns}")
    print(f"- {label} 컬럼을 찾지 못했습니다.")
    return None


def build_ids(dataframe: pd.DataFrame, column: str | None, prefix: str) -> pd.Series:
    if column:
        values = dataframe[column].fillna("").astype(str).str.strip()
        missing_mask = values.eq("")
        if missing_mask.any():
            values.loc[missing_mask] = [f"{prefix}_{index:06d}" for index in range(1, int(missing_mask.sum()) + 1)]
        return values
    return pd.Series([f"{prefix}_{index:06d}" for index in range(1, len(dataframe) + 1)], index=dataframe.index, dtype="string")


def prepare_buildings(buildings: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    work = buildings.copy()
    work["id"] = build_ids(work, "id" if "id" in work.columns else None, prefix="BLDG")
    work["dominant_building_use"] = work.get("main_use", "").fillna("").astype(str).str.strip()
    work["building_area_m2"] = pd.to_numeric(work.get("area_m2", 0), errors="coerce").fillna(0.0)
    missing_area_mask = work["building_area_m2"] <= 0
    work.loc[missing_area_mask, "building_area_m2"] = work.loc[missing_area_mask, "geometry"].area
    return work[["id", "landuse_group", "dominant_building_use", "building_area_m2", "geometry"]].copy()


def prepare_urban_facilities(facilities: gpd.GeoDataFrame, boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    clipped = clip_to_songpa(facilities, boundary, "도시계획 시설")
    if clipped.empty:
        return clipped

    clipped["urban_facility"] = clipped.get("DGM_NM", "").fillna("").astype(str).str.strip()
    clipped["urban_facility_landuse"] = clipped["urban_facility"].apply(classify_urban_facility)
    clipped["urban_facility_source"] = "도시계획 시설정보"
    return clipped[["facility_layer", "urban_facility", "urban_facility_landuse", "urban_facility_source", "geometry"]].copy()


def classify_parcels(
    parcels: gpd.GeoDataFrame,
    buildings: gpd.GeoDataFrame,
    facilities: gpd.GeoDataFrame | None,
) -> gpd.GeoDataFrame:
    result = parcels.copy()
    result["landuse_group"] = pd.NA
    result["legal_basis"] = pd.NA
    result["source_priority"] = pd.NA
    result["dominant_building_use"] = ""
    result["urban_facility"] = ""
    result["zoning"] = ""
    result["building_count"] = 0
    result["match_status"] = ""
    result["confidence"] = "low"
    result["diagnosis"] = ""

    building_based = classify_from_buildings(result, buildings)
    result.update(building_based)

    remaining_mask = result["landuse_group"].isna()
    if remaining_mask.any():
        jimok_based = classify_from_jimok(result.loc[remaining_mask].copy())
        result.loc[remaining_mask, jimok_based.columns] = jimok_based

    remaining_mask = result["landuse_group"].isna()
    if remaining_mask.any() and facilities is not None and not facilities.empty:
        facility_based = classify_from_urban_facilities(result.loc[remaining_mask].copy(), facilities)
        result.loc[remaining_mask, facility_based.columns] = facility_based

    remaining_mask = result["landuse_group"].isna()
    if remaining_mask.any():
        nearby_based = classify_from_nearest_building(result.loc[remaining_mask].copy(), buildings)
        result.loc[remaining_mask, nearby_based.columns] = nearby_based

    remaining_mask = result["landuse_group"].isna()
    if remaining_mask.any():
        result.loc[remaining_mask, "landuse_group"] = "미분류"
        result.loc[remaining_mask, "legal_basis"] = "미분류"
        result.loc[remaining_mask, "source_priority"] = "7_unclassified"
        result.loc[remaining_mask, "match_status"] = "미분류"
        result.loc[remaining_mask, "confidence"] = "low"
        result.loc[remaining_mask, "diagnosis"] = "건축물, 지목, 도시계획시설 정보로도 대표 용도를 판단하기 어려운 필지입니다."

    result["building_count"] = pd.to_numeric(result["building_count"], errors="coerce").fillna(0).astype(int)
    result["dominant_building_use"] = result["dominant_building_use"].fillna("").astype(str)
    result["jimok"] = result["jimok"].fillna("").astype(str)
    result["urban_facility"] = result["urban_facility"].fillna("").astype(str)
    result["zoning"] = result["zoning"].fillna("").astype(str)
    result["diagnosis"] = result["diagnosis"].fillna("").astype(str)
    return result[
        [
            "id",
            "parcel_id",
            "landuse_group",
            "legal_basis",
            "source_priority",
            "dominant_building_use",
            "jimok",
            "urban_facility",
            "zoning",
            "building_count",
            "area_m2",
            "match_status",
            "confidence",
            "diagnosis",
            "geometry",
        ]
    ].copy()


def classify_from_buildings(parcels: gpd.GeoDataFrame, buildings: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[1순위] 건축물 용도 기반 분류를 수행합니다.")
    candidate_pairs = gpd.sjoin(buildings, parcels[["parcel_id", "geometry"]], how="inner", predicate="intersects")
    if candidate_pairs.empty:
        return make_empty_classification_frame(parcels.index)

    parcel_geom_map = parcels.set_index("parcel_id").geometry
    candidate_pairs["parcel_geometry"] = candidate_pairs["parcel_id"].map(parcel_geom_map)
    candidate_pairs["intersection_area_m2"] = candidate_pairs.apply(
        lambda row: row.geometry.intersection(row.parcel_geometry).area, axis=1
    )
    candidate_pairs = candidate_pairs[candidate_pairs["intersection_area_m2"] > 0].copy()
    if candidate_pairs.empty:
        return make_empty_classification_frame(parcels.index)

    candidate_pairs = candidate_pairs.sort_values(
        by=["id", "intersection_area_m2", "building_area_m2"],
        ascending=[True, False, False],
    )
    assigned = candidate_pairs.drop_duplicates(subset=["id"], keep="first").copy()

    grouped = (
        assigned.groupby(["parcel_id", "landuse_group"], dropna=False)
        .agg(
            dominant_building_use=("dominant_building_use", choose_first_text),
            total_building_area_m2=("building_area_m2", "sum"),
            building_count=("id", "count"),
        )
        .reset_index()
    )
    grouped = grouped.sort_values(
        by=["parcel_id", "total_building_area_m2", "building_count", "landuse_group"],
        ascending=[True, False, False, True],
    )
    dominant = grouped.drop_duplicates(subset=["parcel_id"], keep="first").set_index("parcel_id")

    frame = make_empty_classification_frame(parcels.index)
    for index, row in parcels.iterrows():
        parcel_id = row["parcel_id"]
        if parcel_id not in dominant.index:
            continue
        selected = dominant.loc[parcel_id]
        frame.loc[index, "landuse_group"] = selected["landuse_group"]
        frame.loc[index, "legal_basis"] = "건축물 용도 기준"
        frame.loc[index, "source_priority"] = "1_building_use"
        frame.loc[index, "dominant_building_use"] = selected["dominant_building_use"]
        frame.loc[index, "building_count"] = int(selected["building_count"])
        frame.loc[index, "match_status"] = "건물 교차면적 기준"
        frame.loc[index, "confidence"] = "high"
        frame.loc[index, "diagnosis"] = "건물 교차면적 합계가 가장 큰 용도를 대표 용도로 선택했습니다."
    return frame


def classify_from_jimok(parcels: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[2순위] 지목 기반 보조 분류를 적용합니다.")
    frame = make_empty_classification_frame(parcels.index)
    for index, row in parcels.iterrows():
        jimok = str(row.get("jimok", "") or "").strip()
        if not jimok:
            continue
        mapped = match_rule(jimok, JIMOK_RULES)
        if not mapped:
            continue
        frame.loc[index, "landuse_group"] = mapped
        frame.loc[index, "legal_basis"] = "지목 기준"
        frame.loc[index, "source_priority"] = "2_jimok"
        frame.loc[index, "match_status"] = "지목 기반 보조 분류"
        frame.loc[index, "confidence"] = "medium"
        frame.loc[index, "diagnosis"] = f"지목 '{jimok}' 값을 근거로 보조 분류했습니다."
    return frame


def classify_from_urban_facilities(parcels: gpd.GeoDataFrame, facilities: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[3순위] 도시계획 시설 기반 보조 분류를 적용합니다.")
    joined = gpd.overlay(
        parcels[["parcel_id", "geometry"]],
        facilities[["urban_facility", "urban_facility_landuse", "geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if joined.empty:
        return make_empty_classification_frame(parcels.index)

    joined["intersection_area_m2"] = joined.geometry.area
    joined = joined[joined["intersection_area_m2"] > 0].copy()
    joined = joined.sort_values(
        by=["parcel_id", "intersection_area_m2", "urban_facility_landuse"],
        ascending=[True, False, True],
    )
    dominant = joined.drop_duplicates(subset=["parcel_id"], keep="first").set_index("parcel_id")

    frame = make_empty_classification_frame(parcels.index)
    for index, row in parcels.iterrows():
        parcel_id = row["parcel_id"]
        if parcel_id not in dominant.index:
            continue
        selected = dominant.loc[parcel_id]
        if not selected["urban_facility_landuse"]:
            continue
        frame.loc[index, "landuse_group"] = selected["urban_facility_landuse"]
        frame.loc[index, "legal_basis"] = "도시계획 시설 기준"
        frame.loc[index, "source_priority"] = "3_urban_facility"
        frame.loc[index, "urban_facility"] = selected["urban_facility"]
        frame.loc[index, "match_status"] = "도시계획 시설 중첩"
        frame.loc[index, "confidence"] = "medium"
        frame.loc[index, "diagnosis"] = f"도시계획 시설 '{selected['urban_facility']}'와의 중첩을 반영했습니다."
    return frame


def classify_from_nearest_building(parcels: gpd.GeoDataFrame, buildings: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[4순위] 근접 건축물 보조 매칭을 적용합니다.")
    frame = make_empty_classification_frame(parcels.index)
    candidate = parcels[parcels["jimok"].astype(str).str.strip().ne("")].copy()
    if candidate.empty:
        return frame

    candidate = candidate[~candidate["jimok"].astype(str).apply(is_strict_nonbuilding_jimok)].copy()
    if candidate.empty:
        return frame

    parcel_centroids = candidate[["parcel_id", "geometry"]].copy()
    parcel_centroids["geometry"] = parcel_centroids.geometry.centroid
    parcel_centroids = gpd.GeoDataFrame(parcel_centroids, geometry="geometry", crs=TARGET_CRS)

    building_centroids = buildings[["landuse_group", "dominant_building_use", "geometry"]].copy()
    building_centroids["geometry"] = building_centroids.geometry.centroid
    building_centroids = gpd.GeoDataFrame(building_centroids, geometry="geometry", crs=TARGET_CRS)

    nearest = gpd.sjoin_nearest(
        parcel_centroids,
        building_centroids,
        how="left",
        max_distance=NEAR_DISTANCE_M,
        distance_col="distance_m",
    ).dropna(subset=["landuse_group"])

    nearest = nearest.drop_duplicates(subset=["parcel_id"], keep="first").set_index("parcel_id")
    for index, row in parcels.iterrows():
        parcel_id = row["parcel_id"]
        if parcel_id not in nearest.index:
            continue
        selected = nearest.loc[parcel_id]
        frame.loc[index, "landuse_group"] = selected["landuse_group"]
        frame.loc[index, "legal_basis"] = "근접 건축물 보조 매칭"
        frame.loc[index, "source_priority"] = "5_nearest_building"
        frame.loc[index, "dominant_building_use"] = selected["dominant_building_use"]
        frame.loc[index, "match_status"] = "2m 이내 근접 건물"
        frame.loc[index, "confidence"] = "low"
        frame.loc[index, "diagnosis"] = "2m 이내 인접 건축물의 용도를 참고해 보조 추정했습니다."
    return frame


def make_empty_classification_frame(index: pd.Index) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "landuse_group": pd.Series(pd.NA, index=index, dtype="object"),
            "legal_basis": pd.Series(pd.NA, index=index, dtype="object"),
            "source_priority": pd.Series(pd.NA, index=index, dtype="object"),
            "dominant_building_use": pd.Series("", index=index, dtype="object"),
            "urban_facility": pd.Series("", index=index, dtype="object"),
            "zoning": pd.Series("", index=index, dtype="object"),
            "building_count": pd.Series(0, index=index, dtype="int64"),
            "match_status": pd.Series("", index=index, dtype="object"),
            "confidence": pd.Series("low", index=index, dtype="object"),
            "diagnosis": pd.Series("", index=index, dtype="object"),
        }
    )


def match_rule(text: str, rules: list[tuple[list[str], str]]) -> str | None:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return None
    for keywords, label in rules:
        if any(keyword.lower() in normalized for keyword in keywords):
            return label
    return None


def classify_urban_facility(name: str) -> str:
    return match_rule(name, URBAN_FACILITY_RULES) or "기타"


def is_strict_nonbuilding_jimok(jimok: str) -> bool:
    normalized = str(jimok or "").strip().lower()
    return any(keyword in normalized for keyword in ["도로", "하천", "구거", "공원", "학교용지", "철도용지"])


def choose_first_text(values: pd.Series) -> str:
    for value in values:
        if str(value or "").strip():
            return str(value).strip()
    return ""


def create_summary(parcels: gpd.GeoDataFrame) -> pd.DataFrame:
    summary = (
        parcels.groupby("landuse_group", dropna=False)
        .agg(
            area_m2=("area_m2", "sum"),
            parcel_count=("parcel_id", "nunique"),
            building_count=("building_count", "sum"),
        )
        .reset_index()
    )
    total_area = float(summary["area_m2"].sum())
    summary["ratio"] = (summary["area_m2"] / total_area * 100) if total_area > 0 else 0
    summary["area_m2"] = summary["area_m2"].round(1)
    summary["ratio"] = summary["ratio"].round(1)
    summary = summary.sort_values("area_m2", ascending=False).reset_index(drop=True)
    return summary[["landuse_group", "area_m2", "ratio", "parcel_count", "building_count"]]


def create_diagnosis(parcels: gpd.GeoDataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    by_priority = (
        parcels.groupby("source_priority", dropna=False)
        .agg(parcel_count=("parcel_id", "count"), area_m2=("area_m2", "sum"))
        .reset_index()
    )
    for _, row in by_priority.iterrows():
        rows.append(
            {
                "category": "source_priority",
                "name": row["source_priority"] or "(없음)",
                "parcel_count": int(row["parcel_count"]),
                "area_m2": round(float(row["area_m2"]), 1),
            }
        )

    by_confidence = (
        parcels.groupby("confidence", dropna=False)
        .agg(parcel_count=("parcel_id", "count"), area_m2=("area_m2", "sum"))
        .reset_index()
    )
    for _, row in by_confidence.iterrows():
        rows.append(
            {
                "category": "confidence",
                "name": row["confidence"] or "(없음)",
                "parcel_count": int(row["parcel_count"]),
                "area_m2": round(float(row["area_m2"]), 1),
            }
        )

    unclassified = parcels[parcels["landuse_group"] == "미분류"].copy()
    if not unclassified.empty:
        by_jimok = (
            unclassified.groupby("jimok", dropna=False)
            .agg(parcel_count=("parcel_id", "count"), area_m2=("area_m2", "sum"))
            .reset_index()
        )
        for _, row in by_jimok.iterrows():
            rows.append(
                {
                    "category": "unclassified_jimok",
                    "name": row["jimok"] or "(없음)",
                    "parcel_count": int(row["parcel_count"]),
                    "area_m2": round(float(row["area_m2"]), 1),
                }
            )

    for label in ["근접 건축물 보조 매칭", "도시계획 시설 기준", "지목 기준"]:
        subset = parcels[parcels["legal_basis"] == label]
        rows.append(
            {
                "category": "legal_basis",
                "name": label,
                "parcel_count": int(len(subset)),
                "area_m2": round(float(subset["area_m2"].sum()), 1),
            }
        )

    return pd.DataFrame(rows)


def save_geojson(dataframe: gpd.GeoDataFrame, path: Path) -> None:
    web_gdf = dataframe.to_crs(WEB_CRS).copy()
    geojson_text = json.dumps(json.loads(web_gdf.to_json(drop_id=True)), ensure_ascii=False)
    path.write_text(geojson_text, encoding="utf-8")


def print_results(result: gpd.GeoDataFrame, summary: pd.DataFrame, diagnosis: pd.DataFrame) -> None:
    print("\n[결과 요약]")
    print(f"- 총 필지 수: {len(result):,}건")
    print(f"- 총 필지 면적: {result['area_m2'].sum():,.1f}㎡")
    print("- 용도별 요약표")
    print(summary.to_string(index=False))
    print("- 분류 진단표")
    print(diagnosis.to_string(index=False))


def print_header(message: str) -> None:
    print(f"\n=== {message} ===")


if __name__ == "__main__":
    sys.exit(main())
