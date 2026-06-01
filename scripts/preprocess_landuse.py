from __future__ import annotations

import sys
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon


ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_BUILDINGS = ROOT_DIR / "data" / "raw" / "buildings.shp"
INPUT_PARCELS = ROOT_DIR / "data" / "raw" / "parcels.shp"
INPUT_BOUNDARY = ROOT_DIR / "data" / "raw" / "songpa_boundary.geojson"
OUTPUT_DIR = ROOT_DIR / "public" / "data"
OUTPUT_BUILDINGS = OUTPUT_DIR / "buildings_songpa.geojson"
OUTPUT_SUMMARY = OUTPUT_DIR / "landuse_summary.csv"
TARGET_CRS = "EPSG:5179"
WEB_CRS = "EPSG:4326"

USE_COLUMN_CANDIDATES = [
    "main_use",
    "MAIN_USE",
    "main_purps",
    "MAIN_PURPS",
    "주용도",
    "주용도명",
    "용도",
    "용도명",
    "BULD_USE",
    "USE_NM",
    "A25",
    "A24",
    "A26",
]

ADDRESS_COLUMN_CANDIDATES = [
    "address",
    "ADDRESS",
    "대지위치",
    "주소",
    "jibun",
    "JIBUN",
    "A4",
]

ID_COLUMN_CANDIDATES = [
    "id",
    "ID",
    "gid",
    "GID",
    "fid",
    "FID",
    "pk",
    "PK",
    "관리번호",
    "건축물관리번호",
    "A0",
    "A1",
    "A8",
]

PARCEL_ID_CANDIDATES = [
    "pnu",
    "PNU",
    "필지고유번호",
    "고유번호",
    "A1",
]


def main() -> int:
    try:
        print_header("송파구 건축물 용도 분석 데이터 전처리 시작")
        validate_input_paths()

        buildings = read_spatial_file(INPUT_BUILDINGS, "건축물 원본")
        boundary = read_spatial_file(INPUT_BOUNDARY, "송파구 경계")
        parcels = read_spatial_file(INPUT_PARCELS, "연속지적도 필지", required=False)

        buildings = preserve_identifier_columns(buildings)
        boundary = preserve_identifier_columns(boundary)
        parcels = preserve_identifier_columns(parcels) if parcels is not None else None

        buildings = ensure_crs(buildings, "건축물 원본")
        boundary = ensure_crs(boundary, "송파구 경계")
        parcels = ensure_crs(parcels, "연속지적도 필지") if parcels is not None else None

        buildings_5179 = buildings.to_crs(TARGET_CRS)
        boundary_5179 = boundary.to_crs(TARGET_CRS)
        parcels_5179 = parcels.to_crs(TARGET_CRS) if parcels is not None else None

        buildings_5179 = clean_geometries(buildings_5179, "건축물 원본")
        boundary_5179 = clean_geometries(boundary_5179, "송파구 경계")
        parcels_5179 = clean_geometries(parcels_5179, "연속지적도 필지") if parcels is not None else None

        if boundary_5179.empty:
            raise ValueError("송파구 경계 데이터에 유효한 geometry가 없습니다.")

        clipped = clip_to_songpa(buildings_5179, boundary_5179, "건축물")
        if clipped.empty:
            raise ValueError(
                "송파구 경계로 clip한 결과가 비어 있습니다. "
                "입력 데이터의 좌표계 또는 경계 범위를 확인해주세요."
            )

        use_column = find_use_column(clipped)
        address_column = find_address_column(clipped)
        id_column = find_column(clipped, ID_COLUMN_CANDIDATES, "id", required=False)

        clipped["main_use"] = clipped[use_column].fillna("").astype(str).str.strip()
        clipped["landuse_group"] = clipped["main_use"].apply(classify_landuse)
        clipped["address"] = (
            clipped[address_column].fillna("").astype(str).str.strip()
            if address_column
            else ""
        )
        clipped["id"] = build_id_series(clipped, id_column)
        clipped["area_m2"] = clipped.geometry.area

        clipped = clipped[clipped["area_m2"] > 0].copy()
        if clipped.empty:
            raise ValueError(
                "면적 계산 후 area_m2가 0 이하인 건축물만 남았습니다. "
                "입력 geometry 또는 좌표계를 확인해주세요."
            )

        result = clipped[["id", "landuse_group", "main_use", "area_m2", "address", "geometry"]].copy()
        result["area_m2"] = result["area_m2"].round(1)

        parcel_counts = calculate_parcel_counts(result, parcels_5179, boundary_5179)
        summary = create_summary(result, parcel_counts)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        save_geojson(result, OUTPUT_BUILDINGS)
        save_summary(summary, OUTPUT_SUMMARY)

        print_results(result, summary)
        print_header("전처리 완료")
        print(f"- GeoJSON 저장: {OUTPUT_BUILDINGS}")
        print(f"- CSV 저장: {OUTPUT_SUMMARY}")
        return 0

    except Exception as error:
        print("\n[오류] 전처리 중 문제가 발생했습니다.", file=sys.stderr)
        print(f"- 원인: {error}", file=sys.stderr)
        print(
            "- 확인 사항: 입력 파일 존재 여부, 좌표계 정의 여부, 용도 컬럼명, geometry 상태를 점검해주세요.",
            file=sys.stderr,
        )
        return 1


def validate_input_paths() -> None:
    missing = [str(path) for path in [INPUT_BUILDINGS, INPUT_BOUNDARY] if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "필수 입력 파일을 찾지 못했습니다.\n"
            + "\n".join(f"- {path}" for path in missing)
        )


def read_spatial_file(path: Path, label: str, required: bool = True) -> gpd.GeoDataFrame | None:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"{label} 파일이 존재하지 않습니다: {path}")
        print(f"\n[{label}] 파일이 없어 이 단계는 건너뜁니다: {path}")
        return None

    encodings = ["cp949", "utf-8"]
    errors: list[str] = []

    for encoding in encodings:
        try:
            print(f"\n[{label}] 읽는 중... encoding={encoding}")
            dataframe = gpd.read_file(path, engine="pyogrio", encoding=encoding)
            print(f"- 성공: {len(dataframe):,}건, 컬럼 {len(dataframe.columns)}개")
            print(f"- 컬럼 목록: {list(dataframe.columns)}")
            return dataframe
        except Exception as error:
            errors.append(f"encoding={encoding}: {error}")

    if required:
        raise RuntimeError(
            f"{label} 파일을 읽지 못했습니다.\n"
            f"- 경로: {path}\n"
            + "\n".join(f"- 시도 실패: {message}" for message in errors)
        )

    print(f"\n[{label}] 읽기에 실패해 필지 수 계산을 건너뜁니다.")
    for message in errors:
        print(f"- {message}")
    return None


def preserve_identifier_columns(dataframe: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame | None:
    if dataframe is None:
        return None
    dataframe = dataframe.copy()
    for column in dataframe.columns:
        if column == dataframe.geometry.name:
            continue
        lowered = str(column).lower()
        if any(keyword in lowered for keyword in ["id", "pk", "code", "관리", "번호"]):
            dataframe[column] = dataframe[column].astype("string")
    return dataframe


def ensure_crs(dataframe: gpd.GeoDataFrame | None, label: str) -> gpd.GeoDataFrame | None:
    if dataframe is None:
        return None
    if dataframe.crs is None:
        raise ValueError(
            f"{label} 데이터에 좌표계 정보(CRS)가 없습니다. "
            "원본 파일의 .prj 또는 좌표계 메타데이터를 확인한 뒤 다시 실행해주세요."
        )
    print(f"- {label} CRS: {dataframe.crs}")
    return dataframe


def clean_geometries(dataframe: gpd.GeoDataFrame | None, label: str) -> gpd.GeoDataFrame | None:
    if dataframe is None:
        return None
    dataframe = dataframe.copy()
    before_count = len(dataframe)
    dataframe = dataframe[~dataframe.geometry.isna()].copy()
    dataframe = dataframe[~dataframe.geometry.is_empty].copy()
    dataframe["geometry"] = dataframe.geometry.buffer(0)
    dataframe = dataframe[~dataframe.geometry.isna()].copy()
    dataframe = dataframe[~dataframe.geometry.is_empty].copy()
    dataframe["geometry"] = dataframe.geometry.apply(extract_polygonal_geometry)
    dataframe = dataframe[~dataframe.geometry.isna()].copy()
    dataframe = dataframe[~dataframe.geometry.is_empty].copy()
    dataframe = dataframe[dataframe.geometry.is_valid].copy()
    removed = before_count - len(dataframe)
    print(f"- {label} geometry 정리 후 {len(dataframe):,}건 유지, {removed:,}건 제거")
    return dataframe


def extract_polygonal_geometry(geometry):
    if geometry is None or geometry.is_empty:
        return None
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry
    if isinstance(geometry, GeometryCollection):
        polygons = [geom for geom in geometry.geoms if isinstance(geom, (Polygon, MultiPolygon))]
        if not polygons:
            return None
        flattened = []
        for polygon in polygons:
            if isinstance(polygon, Polygon):
                flattened.append(polygon)
            else:
                flattened.extend(list(polygon.geoms))
        return MultiPolygon(flattened) if len(flattened) > 1 else flattened[0]
    return None


def clip_to_songpa(dataframe: gpd.GeoDataFrame, boundary: gpd.GeoDataFrame, label: str) -> gpd.GeoDataFrame:
    print(f"\n[공간 클립] 송파구 경계 기준으로 {label} 필터링")
    clipped = gpd.clip(dataframe, boundary)
    clipped = clean_geometries(clipped, f"{label} 클립 결과")
    print(f"- 송파구 경계 내 {label} 수: {len(clipped):,}건")
    return clipped


def find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
    label: str,
    required: bool = True,
) -> str | None:
    columns = list(dataframe.columns)
    for candidate in candidates:
        if candidate in columns:
            print(f"- {label} 컬럼 선택: {candidate}")
            return candidate

    if required:
        raise ValueError(
            f"{label}에 해당하는 컬럼을 찾지 못했습니다.\n"
            f"- 찾은 컬럼 목록: {columns}\n"
            f"- 확인한 후보: {candidates}\n"
            f"- 원본 데이터의 실제 컬럼명을 확인해 후보 목록에 추가해주세요."
        )

    print(f"- {label} 컬럼 없음: 빈 값으로 대체합니다.")
    return None


def find_use_column(dataframe: pd.DataFrame) -> str:
    direct_match = find_column(dataframe, USE_COLUMN_CANDIDATES, "주용도", required=False)
    if direct_match:
        return direct_match

    inferred = infer_column_by_keywords(
        dataframe=dataframe,
        keywords=[
            "단독주택",
            "공동주택",
            "근린생활",
            "업무",
            "사무",
            "오피스텔",
            "판매",
            "시장",
            "교육",
            "연구",
            "학교",
            "학원",
            "의료",
            "병원",
            "의원",
            "노유자",
            "어린이집",
            "요양",
            "운동",
            "체육",
            "숙박",
            "호텔",
            "여관",
            "위락",
            "유흥",
        ],
        label="주용도",
        min_hits=10,
    )
    if inferred:
        return inferred

    columns = list(dataframe.columns)
    raise ValueError(
        "주용도에 해당하는 컬럼을 찾지 못했습니다.\n"
        f"- 현재 컬럼 목록: {columns}\n"
        f"- 확인한 후보: {USE_COLUMN_CANDIDATES}\n"
        "- 익명 컬럼(A25 등) 구조일 수 있으니 샘플 값을 확인해 후보 목록을 보강해주세요."
    )


def find_address_column(dataframe: pd.DataFrame) -> str | None:
    direct_match = find_column(dataframe, ADDRESS_COLUMN_CANDIDATES, "주소", required=False)
    if direct_match:
        return direct_match

    return infer_column_by_keywords(
        dataframe=dataframe,
        keywords=["서울", "송파구", "로", "길", "동", "지하", "번지"],
        label="주소",
        min_hits=10,
    )


def infer_column_by_keywords(
    dataframe: pd.DataFrame,
    keywords: list[str],
    label: str,
    min_hits: int = 5,
) -> str | None:
    best_column = None
    best_hits = 0

    for column in dataframe.columns:
        if column == "geometry":
            continue

        series = dataframe[column].dropna()
        if series.empty:
            continue

        sample = series.astype(str).str.strip().head(500)
        hits = sample.apply(lambda value: any(keyword in value for keyword in keywords)).sum()

        if hits > best_hits:
            best_hits = int(hits)
            best_column = column

    if best_column and best_hits >= min_hits:
        print(f"- {label} 컬럼 추론: {best_column} (키워드 일치 {best_hits}건)")
        return best_column

    return None


def build_id_series(dataframe: pd.DataFrame, id_column: str | None) -> pd.Series:
    if id_column:
        values = dataframe[id_column].fillna("").astype(str).str.strip()
        missing_mask = values.eq("")
        if missing_mask.any():
            values.loc[missing_mask] = [
                f"BLDG_{index:06d}" for index in range(1, int(missing_mask.sum()) + 1)
            ]
        return values

    return pd.Series(
        [f"BLDG_{index:06d}" for index in range(1, len(dataframe) + 1)],
        index=dataframe.index,
        dtype="string",
    )


def calculate_parcel_counts(
    buildings: gpd.GeoDataFrame,
    parcels: gpd.GeoDataFrame | None,
    boundary: gpd.GeoDataFrame,
) -> pd.DataFrame | None:
    if parcels is None:
        print("\n[필지 수 계산] 필지 원본이 없어 parcel_count를 비워둡니다.")
        return None

    try:
        clipped_parcels = clip_to_songpa(parcels, boundary, "필지")
        if clipped_parcels.empty:
            print("\n[필지 수 계산] 송파구 경계 내 필지가 없어 parcel_count를 비워둡니다.")
            return None

        parcel_id_column = find_column(clipped_parcels, PARCEL_ID_CANDIDATES, "필지 고유번호")
        parcel_work = clipped_parcels[[parcel_id_column, "geometry"]].copy()
        parcel_work["parcel_id"] = parcel_work[parcel_id_column].fillna("").astype(str).str.strip()
        parcel_work = parcel_work[parcel_work["parcel_id"].ne("")].copy()

        if parcel_work.empty:
            print("\n[필지 수 계산] 사용할 수 있는 필지 고유번호가 없어 parcel_count를 비워둡니다.")
            return None

        building_centroids = buildings[["id", "landuse_group", "geometry"]].copy()
        building_centroids["geometry"] = building_centroids.geometry.centroid
        building_centroids = gpd.GeoDataFrame(building_centroids, geometry="geometry", crs=TARGET_CRS)

        joined = gpd.sjoin(
            building_centroids,
            gpd.GeoDataFrame(parcel_work[["parcel_id", "geometry"]], geometry="geometry", crs=TARGET_CRS),
            how="left",
            predicate="within",
        )
        joined = joined.dropna(subset=["parcel_id"]).copy()

        if joined.empty:
            print("\n[필지 수 계산] 건축물 중심점과 일치하는 필지를 찾지 못해 parcel_count를 비워둡니다.")
            return None

        summary = (
            joined.groupby("landuse_group", dropna=False)["parcel_id"]
            .nunique()
            .reset_index(name="parcel_count")
        )
        summary["parcel_count"] = summary["parcel_count"].astype("Int64")

        print("\n[필지 수 계산] 용도별 고유 필지 수 계산 완료")
        print(summary.to_string(index=False))
        return summary

    except Exception as error:
        print("\n[필지 수 계산] 필지 수 계산에 실패했습니다. parcel_count는 빈 값으로 저장합니다.")
        print(f"- 원인: {error}")
        return None


def classify_landuse(main_use: str) -> str:
    normalized = (main_use or "").strip().lower()
    if not normalized:
        return "기타"

    rules = [
        (["단독주택", "다가구"], "단독주택"),
        (["아파트", "연립", "다세대", "공동주택"], "공동주택"),
        (["근린생활"], "근린생활시설"),
        (["업무", "사무", "오피스텔"], "업무시설"),
        (["판매", "시장"], "판매시설"),
        (["교육", "연구", "학교", "학원"], "교육연구시설"),
        (["의료", "병원", "의원", "노유자", "어린이집", "요양"], "의료/노유자시설"),
        (["운동", "체육"], "운동시설"),
        (["숙박", "호텔", "여관"], "숙박시설"),
        (["위락", "유흥"], "위락시설"),
    ]

    for keywords, group_name in rules:
        if any(keyword in normalized for keyword in keywords):
            return group_name
    return "기타"


def create_summary(dataframe: gpd.GeoDataFrame, parcel_counts: pd.DataFrame | None = None) -> pd.DataFrame:
    summary = (
        dataframe.groupby("landuse_group", dropna=False)
        .agg(area_m2=("area_m2", "sum"), count=("id", "count"))
        .reset_index()
    )
    if parcel_counts is not None:
        summary = summary.merge(parcel_counts, on="landuse_group", how="left")
    else:
        summary["parcel_count"] = pd.Series([pd.NA] * len(summary), dtype="Int64")
    total_area = summary["area_m2"].sum()
    summary["ratio"] = (summary["area_m2"] / total_area * 100) if total_area > 0 else 0
    summary["area_m2"] = summary["area_m2"].round(1)
    summary["ratio"] = summary["ratio"].round(1)
    summary = summary.sort_values("area_m2", ascending=False).reset_index(drop=True)
    return summary[["landuse_group", "area_m2", "ratio", "count", "parcel_count"]]


def save_geojson(dataframe: gpd.GeoDataFrame, path: Path) -> None:
    web_gdf = dataframe.to_crs(WEB_CRS).copy()
    geojson_text = json.dumps(json.loads(web_gdf.to_json(drop_id=True)), ensure_ascii=False)
    path.write_text(geojson_text, encoding="utf-8")


def save_summary(summary: pd.DataFrame, path: Path) -> None:
    summary.to_csv(path, index=False, encoding="utf-8-sig")


def print_results(result: gpd.GeoDataFrame, summary: pd.DataFrame) -> None:
    total_count = len(result)
    total_area = float(result["area_m2"].sum())
    print("\n[결과 요약]")
    print(f"- 총 건축물 수: {total_count:,}건")
    print(f"- 총 면적: {total_area:,.1f}㎡")
    print("- 용도별 요약표:")
    print(summary.to_string(index=False))


def print_header(message: str) -> None:
    print(f"\n=== {message} ===")


if __name__ == "__main__":
    sys.exit(main())
