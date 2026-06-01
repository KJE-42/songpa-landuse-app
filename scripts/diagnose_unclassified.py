from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_PARCELS = ROOT_DIR / "public" / "data" / "parcels_songpa.geojson"
INPUT_BUILDINGS = ROOT_DIR / "public" / "data" / "buildings_songpa.geojson"
INPUT_FACILITIES = ROOT_DIR / "public" / "data" / "urban_facilities_songpa.geojson"
INPUT_ZONING = ROOT_DIR / "public" / "data" / "zoning_songpa.geojson"
OUTPUT_CLASSIFICATION = ROOT_DIR / "public" / "data" / "classification_diagnosis.csv"
OUTPUT_UNCLASSIFIED = ROOT_DIR / "public" / "data" / "unclassified_diagnosis.csv"
TARGET_CRS = "EPSG:5179"


def main() -> int:
    try:
        parcels = read_required(INPUT_PARCELS, "필지 결과")
        buildings = read_required(INPUT_BUILDINGS, "건축물 결과")
        facilities = read_optional(INPUT_FACILITIES, "도시계획 시설")
        zoning = read_optional(INPUT_ZONING, "용도지역/지구")

        parcels = ensure_metric_crs(parcels, "필지 결과")
        buildings = ensure_metric_crs(buildings, "건축물 결과")
        facilities = ensure_metric_crs(facilities, "도시계획 시설") if facilities is not None else None
        zoning = ensure_metric_crs(zoning, "용도지역/지구") if zoning is not None else None

        classification = build_classification_diagnosis(parcels)
        unclassified = build_unclassified_diagnosis(parcels, buildings, facilities, zoning)

        classification.to_csv(OUTPUT_CLASSIFICATION, index=False, encoding="utf-8-sig")
        unclassified.to_csv(OUTPUT_UNCLASSIFIED, index=False, encoding="utf-8-sig")

        print("\n[분류 진단 요약]")
        print(classification.to_string(index=False))
        print("\n[미분류 진단 요약]")
        print(unclassified.to_string(index=False))
        print(f"\n- 분류 진단 저장: {OUTPUT_CLASSIFICATION}")
        print(f"- 미분류 진단 저장: {OUTPUT_UNCLASSIFIED}")
        return 0
    except Exception as error:
        print(f"[오류] 미분류 진단 실패: {error}", file=sys.stderr)
        return 1


def read_required(path: Path, label: str) -> gpd.GeoDataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일이 없습니다: {path}")
    return gpd.read_file(path, engine="pyogrio", encoding="utf-8")


def read_optional(path: Path, label: str) -> gpd.GeoDataFrame | None:
    if not path.exists():
        print(f"- {label} 파일이 없어 선택 진단을 건너뜁니다: {path.name}")
        return None
    return gpd.read_file(path, engine="pyogrio", encoding="utf-8")


def ensure_metric_crs(dataframe: gpd.GeoDataFrame, label: str) -> gpd.GeoDataFrame:
    if dataframe.crs is None:
        raise ValueError(f"{label}에 CRS 정보가 없습니다.")
    return dataframe.to_crs(TARGET_CRS)


def build_classification_diagnosis(parcels: gpd.GeoDataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_area = numeric_sum(parcels, "area_m2")

    rows.append(make_row("summary", "전체 필지 수", len(parcels), total_area, total_area))

    by_landuse = (
        parcels.groupby("landuse_group", dropna=False)
        .agg(parcel_count=("parcel_id", "count"), area_m2=("area_m2", "sum"))
        .reset_index()
        .sort_values("area_m2", ascending=False)
    )
    for _, row in by_landuse.iterrows():
        rows.append(
            make_row(
                "landuse_group",
                row["landuse_group"] or "(없음)",
                int(row["parcel_count"]),
                float(row["area_m2"]),
                total_area,
            )
        )

    by_priority = (
        parcels.groupby("source_priority", dropna=False)
        .agg(parcel_count=("parcel_id", "count"), area_m2=("area_m2", "sum"))
        .reset_index()
        .sort_values("area_m2", ascending=False)
    )
    for _, row in by_priority.iterrows():
        rows.append(
            make_row(
                "source_priority",
                row["source_priority"] or "(없음)",
                int(row["parcel_count"]),
                float(row["area_m2"]),
                total_area,
            )
        )

    by_confidence = (
        parcels.groupby("confidence", dropna=False)
        .agg(parcel_count=("parcel_id", "count"), area_m2=("area_m2", "sum"))
        .reset_index()
        .sort_values("area_m2", ascending=False)
    )
    for _, row in by_confidence.iterrows():
        rows.append(
            make_row(
                "confidence",
                row["confidence"] or "(없음)",
                int(row["parcel_count"]),
                float(row["area_m2"]),
                total_area,
            )
        )

    return pd.DataFrame(rows)


def build_unclassified_diagnosis(
    parcels: gpd.GeoDataFrame,
    buildings: gpd.GeoDataFrame,
    facilities: gpd.GeoDataFrame | None,
    zoning: gpd.GeoDataFrame | None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_area = numeric_sum(parcels, "area_m2")
    unclassified = parcels[parcels["landuse_group"].fillna("") == "미분류"].copy()
    unclassified_area = numeric_sum(unclassified, "area_m2")
    jimok_series = text_series(unclassified, "jimok")
    zoning_series = text_series(unclassified, "zoning")
    facility_series = text_series(unclassified, "urban_facility")
    source_priority_series = text_series(unclassified, "source_priority")
    match_status_series = text_series(unclassified, "match_status")

    rows.append(make_row("summary", "전체 필지 수", len(parcels), total_area, total_area))
    rows.append(make_row("summary", "전체 필지 면적", len(parcels), total_area, total_area))
    rows.append(make_row("summary", "미분류 필지 수", len(unclassified), unclassified_area, total_area))

    if unclassified.empty:
        return pd.DataFrame(rows)

    empty_building = unclassified[pd.to_numeric(unclassified.get("building_count", 0), errors="coerce").fillna(0) <= 0]
    rows.append(
        make_row(
            "unclassified_reason",
            "건물 매칭 0건",
            len(empty_building),
            numeric_sum(empty_building, "area_m2"),
            unclassified_area,
        )
    )

    jimok_exists = unclassified[jimok_series.str.strip().ne("")]
    rows.append(
        make_row(
            "unclassified_reason",
            "지목 값 존재",
            len(jimok_exists),
            numeric_sum(jimok_exists, "area_m2"),
            unclassified_area,
        )
    )

    near_building = unclassified[source_priority_series.eq("5_nearest_building")]
    rows.append(
        make_row(
            "unclassified_reason",
            "2m 이내 근접 건물 보조 적용",
            len(near_building),
            numeric_sum(near_building, "area_m2"),
            unclassified_area,
        )
    )

    if facilities is not None and not facilities.empty:
        facility_hits = count_spatial_overlap(unclassified, facilities)
        rows.append(
            make_row(
                "unclassified_reason",
                "도시계획 시설 중첩",
                facility_hits["count"],
                facility_hits["area_m2"],
                unclassified_area,
            )
        )

    if zoning is not None and not zoning.empty:
        zoning_hits = count_spatial_overlap(unclassified, zoning)
        rows.append(
            make_row(
                "unclassified_reason",
                "용도지역/지구 중첩",
                zoning_hits["count"],
                zoning_hits["area_m2"],
                unclassified_area,
            )
        )

    true_no_evidence = unclassified[
        jimok_series.str.strip().eq("")
        & pd.to_numeric(unclassified.get("building_count", 0), errors="coerce").fillna(0).le(0)
        & facility_series.str.strip().eq("")
        & zoning_series.str.strip().eq("")
    ]
    rows.append(
        make_row(
            "unclassified_reason",
            "실질적 근거 없음",
            len(true_no_evidence),
            numeric_sum(true_no_evidence, "area_m2"),
            unclassified_area,
        )
    )

    by_jimok = (
        unclassified.groupby(jimok_series.replace("", "(없음)").fillna("(없음)"))
        .agg(parcel_count=("parcel_id", "count"), area_m2=("area_m2", "sum"))
        .reset_index()
        .sort_values("area_m2", ascending=False)
    )
    by_jimok = by_jimok.rename(columns={"jimok": "name", 0: "name"})
    for _, row in by_jimok.head(15).iterrows():
        rows.append(
            make_row(
                "unclassified_jimok",
                row["name"],
                int(row["parcel_count"]),
                float(row["area_m2"]),
                unclassified_area,
            )
        )

    by_match_status = (
        unclassified.groupby(match_status_series.replace("", "(없음)").fillna("(없음)"))
        .agg(parcel_count=("parcel_id", "count"), area_m2=("area_m2", "sum"))
        .reset_index()
        .sort_values("area_m2", ascending=False)
    )
    by_match_status = by_match_status.rename(columns={"match_status": "name", 0: "name"})
    for _, row in by_match_status.iterrows():
        rows.append(
            make_row(
                "unclassified_match_status",
                row["name"],
                int(row["parcel_count"]),
                float(row["area_m2"]),
                unclassified_area,
            )
        )

    return pd.DataFrame(rows)


def count_spatial_overlap(source: gpd.GeoDataFrame, target: gpd.GeoDataFrame) -> dict[str, float]:
    joined = gpd.overlay(
        source[["parcel_id", "area_m2", "geometry"]],
        target[["geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if joined.empty:
        return {"count": 0, "area_m2": 0.0}
    joined["intersection_area_m2"] = joined.geometry.area
    grouped = (
        joined.groupby("parcel_id", dropna=False)
        .agg(intersection_area_m2=("intersection_area_m2", "sum"))
        .reset_index()
    )
    return {
        "count": int(len(grouped)),
        "area_m2": round(float(grouped["intersection_area_m2"].sum()), 1),
    }


def numeric_sum(dataframe: gpd.GeoDataFrame | pd.DataFrame, column: str) -> float:
    if column not in dataframe.columns:
        return 0.0
    return round(float(pd.to_numeric(dataframe[column], errors="coerce").fillna(0).sum()), 1)


def text_series(dataframe: gpd.GeoDataFrame | pd.DataFrame, column: str) -> pd.Series:
    if column not in dataframe.columns:
        return pd.Series("", index=dataframe.index, dtype="object")
    return dataframe[column].fillna("").astype(str)


def make_row(category: str, name: str, parcel_count: int, area_m2: float, total_area: float) -> dict[str, object]:
    ratio = round((area_m2 / total_area * 100), 1) if total_area > 0 else 0.0
    return {
        "category": category,
        "name": name,
        "parcel_count": int(parcel_count),
        "area_m2": round(float(area_m2), 1),
        "ratio": ratio,
    }


if __name__ == "__main__":
    sys.exit(main())
