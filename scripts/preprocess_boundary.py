from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd


ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_BOUNDARY = ROOT_DIR / "data" / "raw" / "sigungu_boundary.shp"
OUTPUT_BOUNDARY = ROOT_DIR / "public" / "data" / "songpa_boundary.geojson"
TARGET_CRS = "EPSG:4326"

BOUNDARY_NAME_CANDIDATES = [
    "SIG_KOR_NM",
    "SGG_NM",
    "시군구명",
    "SIGUNGU_NM",
    "ADM_NM",
    "행정구역명",
    "NAME",
    "SIG_CD",
]


def main() -> int:
    try:
        print_header("송파구 경계 전처리 시작")
        validate_input_path()

        boundary = read_spatial_file(INPUT_BOUNDARY, "시군구 경계")
        boundary = ensure_crs(boundary, "시군구 경계")
        boundary = boundary.to_crs(TARGET_CRS)
        boundary = clean_geometries(boundary, "시군구 경계")

        name_column, songpa = find_songpa_rows(boundary)

        songpa["geometry"] = songpa.geometry.buffer(0)
        songpa = clean_geometries(songpa, "송파구 경계")

        OUTPUT_BOUNDARY.parent.mkdir(parents=True, exist_ok=True)
        save_geojson(songpa, OUTPUT_BOUNDARY)

        print_results(songpa)
        print_header("송파구 경계 전처리 완료")
        print(f"- 저장 경로: {OUTPUT_BOUNDARY}")
        return 0

    except Exception as error:
        print("\n[오류] 송파구 경계 전처리 중 문제가 발생했습니다.", file=sys.stderr)
        print(f"- 원인: {error}", file=sys.stderr)
        print(
            "- 확인 사항: 입력 SHP 경로, CRS 정의, 시군구명 컬럼명, geometry 상태를 점검해주세요.",
            file=sys.stderr,
        )
        return 1


def validate_input_path() -> None:
    if not INPUT_BOUNDARY.exists():
        raise FileNotFoundError(f"입력 파일을 찾지 못했습니다: {INPUT_BOUNDARY}")


def read_spatial_file(path: Path, label: str) -> gpd.GeoDataFrame:
    encodings = ["cp949", "utf-8"]
    errors: list[str] = []

    for encoding in encodings:
        try:
            print(f"\n[{label}] 읽는 중... encoding={encoding}")
            dataframe = gpd.read_file(path, engine="pyogrio", encoding=encoding)
            print(f"- 성공: {len(dataframe):,}건")
            print(f"- 컬럼 목록: {list(dataframe.columns)}")
            return dataframe
        except Exception as error:
            errors.append(f"encoding={encoding}: {error}")

    raise RuntimeError(
        f"{label} 파일을 읽지 못했습니다.\n"
        f"- 경로: {path}\n"
        + "\n".join(f"- 시도 실패: {message}" for message in errors)
    )


def ensure_crs(dataframe: gpd.GeoDataFrame, label: str) -> gpd.GeoDataFrame:
    if dataframe.crs is None:
        raise ValueError(
            f"{label} 데이터에 좌표계 정보(CRS)가 없습니다. "
            "원본 파일의 .prj 또는 메타데이터를 확인해주세요."
        )
    print(f"- {label} 원본 CRS: {dataframe.crs}")
    return dataframe


def clean_geometries(dataframe: gpd.GeoDataFrame, label: str) -> gpd.GeoDataFrame:
    dataframe = dataframe.copy()
    before_count = len(dataframe)
    dataframe = dataframe[~dataframe.geometry.isna()].copy()
    dataframe = dataframe[~dataframe.geometry.is_empty].copy()
    dataframe["geometry"] = dataframe.geometry.buffer(0)
    dataframe = dataframe[~dataframe.geometry.isna()].copy()
    dataframe = dataframe[~dataframe.geometry.is_empty].copy()
    dataframe = dataframe[dataframe.geometry.is_valid].copy()
    removed = before_count - len(dataframe)
    print(f"- {label} geometry 정리 후 {len(dataframe):,}건 유지, {removed:,}건 제거")
    return dataframe


def find_songpa_rows(dataframe: gpd.GeoDataFrame) -> tuple[str, gpd.GeoDataFrame]:
    columns = list(dataframe.columns)

    for candidate in BOUNDARY_NAME_CANDIDATES:
        if candidate not in columns or candidate == "geometry":
            continue

        series = dataframe[candidate].fillna("").astype(str)
        matched = dataframe[series.str.contains("송파구", na=False, regex=False)].copy()
        if not matched.empty:
            print(f"- 송파구 필터링 컬럼 선택: {candidate}")
            return candidate, matched

    string_columns = get_string_columns(dataframe)
    for column in string_columns:
        series = dataframe[column].fillna("").astype(str)
        matched = dataframe[series.str.contains("송파구", na=False, regex=False)].copy()
        if not matched.empty:
            print(f"- 송파구 필터링 컬럼 추론: {column}")
            return column, matched

    debug_text = build_debug_text(dataframe, string_columns)
    raise ValueError(
        "시군구 경계 데이터에서 값에 '송파구'가 포함된 행을 찾지 못했습니다.\n"
        f"- 현재 컬럼 목록: {columns}\n"
        f"- 후보 컬럼: {BOUNDARY_NAME_CANDIDATES}\n"
        f"{debug_text}"
    )


def get_string_columns(dataframe: gpd.GeoDataFrame) -> list[str]:
    string_columns: list[str] = []
    for column in dataframe.columns:
        if column == "geometry":
            continue
        series = dataframe[column]
        dtype_name = str(series.dtype).lower()
        if (
            series.dtype == "object"
            or dtype_name.startswith("string")
            or dtype_name == "str"
            or dtype_name == "string"
        ):
            string_columns.append(column)
    return string_columns


def build_debug_text(dataframe: gpd.GeoDataFrame, string_columns: list[str]) -> str:
    if not string_columns:
        return "- 문자열 컬럼을 찾지 못했습니다."

    lines = ["- 문자열 컬럼 고유값 일부:"]
    for column in string_columns[:10]:
        samples = (
            dataframe[column]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda series: series.ne("")]
            .drop_duplicates()
            .head(8)
            .tolist()
        )
        lines.append(f"  - {column}: {samples}")
    return "\n".join(lines)


def save_geojson(dataframe: gpd.GeoDataFrame, path: Path) -> None:
    geojson_text = json.dumps(json.loads(dataframe.to_json(drop_id=True)), ensure_ascii=False)
    path.write_text(geojson_text, encoding="utf-8")


def print_results(dataframe: gpd.GeoDataFrame) -> None:
    minx, miny, maxx, maxy = dataframe.total_bounds
    print("\n[결과 요약]")
    print(f"- feature 수: {len(dataframe):,}")
    print(f"- CRS: {dataframe.crs}")
    print(f"- bounds: [{minx:.6f}, {miny:.6f}, {maxx:.6f}, {maxy:.6f}]")
    print(f"- 좌표점 개수: {count_coordinates(dataframe):,}")


def count_coordinates(dataframe: gpd.GeoDataFrame) -> int:
    total = 0
    for geometry in dataframe.geometry:
        if geometry.geom_type == "Polygon":
            total += len(geometry.exterior.coords)
        elif geometry.geom_type == "MultiPolygon":
            for polygon in geometry.geoms:
                total += len(polygon.exterior.coords)
    return total


def print_header(message: str) -> None:
    print(f"\n=== {message} ===")


if __name__ == "__main__":
    sys.exit(main())
