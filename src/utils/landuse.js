import { LANDUSE_ORDER } from './colors';

function createPolygonFeature(properties, coordinates) {
  return {
    type: 'Feature',
    properties,
    geometry: {
      type: 'Polygon',
      coordinates: [coordinates],
    },
  };
}

const sampleBoundary = {
  type: 'FeatureCollection',
  features: [
    createPolygonFeature(
      { name: '송파구 샘플 경계' },
      [
        [127.073, 37.474],
        [127.142, 37.474],
        [127.142, 37.534],
        [127.073, 37.534],
        [127.073, 37.474],
      ],
    ),
  ],
};

const sampleBuildings = {
  type: 'FeatureCollection',
  features: [
    createPolygonFeature(
      {
        id: 'BLDG_000001',
        landuse_group: '공동주택',
        main_use: '아파트',
        area_m2: 12840.3,
        address: '서울특별시 송파구 샘플로 101',
      },
      [
        [127.0838, 37.5134],
        [127.0855, 37.5134],
        [127.0855, 37.5146],
        [127.0838, 37.5146],
        [127.0838, 37.5134],
      ],
    ),
  ],
};

const sampleParcels = {
  type: 'FeatureCollection',
  features: [
    createPolygonFeature(
      {
        id: 'PCL_000001',
        parcel_id: 'PCL_000001',
        landuse_group: '공동주택',
        legal_basis: '건축물 용도 기준',
        source_priority: '1_building_use',
        dominant_building_use: '아파트',
        jimok: '대',
        urban_facility: '',
        zoning: '제3종일반주거지역',
        building_count: 1,
        area_m2: 18620.1,
        match_status: '건물 교차면적 기준',
        confidence: 'high',
        diagnosis: '건물 교차면적 합계가 가장 큰 공동주택으로 분류되었습니다.',
      },
      [
        [127.0832, 37.5128],
        [127.0861, 37.5128],
        [127.0861, 37.5152],
        [127.0832, 37.5152],
        [127.0832, 37.5128],
      ],
    ),
    createPolygonFeature(
      {
        id: 'PCL_000002',
        parcel_id: 'PCL_000002',
        landuse_group: '공원/녹지',
        legal_basis: '도시계획 시설 기준',
        source_priority: '3_urban_facility',
        dominant_building_use: '',
        jimok: '',
        urban_facility: '근린공원',
        zoning: '',
        building_count: 0,
        area_m2: 4922.7,
        match_status: '도시계획 시설 중첩',
        confidence: 'medium',
        diagnosis: '공원 시설과의 중첩으로 공원/녹지로 분류되었습니다.',
      },
      [
        [127.1115, 37.5121],
        [127.1135, 37.5121],
        [127.1135, 37.5139],
        [127.1115, 37.5139],
        [127.1115, 37.5121],
      ],
    ),
  ],
};

const sampleBuildingSummaryCsv = `landuse_group,area_m2,ratio,count,parcel_count
공동주택,12840.3,100.0,1,1`;

const sampleParcelSummaryCsv = `landuse_group,area_m2,ratio,parcel_count,building_count
공동주택,18620.1,79.1,1,1
공원/녹지,4922.7,20.9,1,0`;

export const SAMPLE_DATA = {
  boundary: sampleBoundary,
  buildings: sampleBuildings,
  parcels: sampleParcels,
  buildingSummaryCsv: sampleBuildingSummaryCsv,
  parcelSummaryCsv: sampleParcelSummaryCsv,
};

export const INITIAL_VISIBLE_LANDUSES = [...LANDUSE_ORDER];

export const DATA_PATHS = {
  boundary: '/data/songpa_boundary.geojson',
  buildings: '/data/buildings_songpa.geojson',
  buildingSummary: '/data/landuse_summary.csv',
  parcels: '/data/parcels_songpa.geojson',
  parcelSummary: '/data/parcels_landuse_summary.csv',
  urbanFacilities: '/data/urban_facilities_songpa.geojson',
  classificationDiagnosis: '/data/classification_diagnosis.csv',
  unclassifiedDiagnosis: '/data/unclassified_diagnosis.csv',
};

export const SUMMARY_SCOPE_OPTIONS = [
  { key: 'all', label: '전체 필지 포함' },
  { key: 'exclude_transport', label: '도로/교통시설 제외' },
  { key: 'exclude_transport_water', label: '도로/교통시설 + 하천/수공간 제외' },
  {
    key: 'exclude_transport_water_park',
    label: '도로/교통시설 + 하천/수공간 + 공원/녹지 제외',
  },
  { key: 'building_only', label: '건축물 용도 기준만 보기' },
  { key: 'include_supporting', label: '법 기준 보조분류 포함' },
];

const DEFAULT_LOAD_ERROR_MESSAGE =
  '데이터 파일을 불러오지 못했습니다. public/data 폴더를 확인하세요.';
const DEFAULT_PARCEL_FALLBACK_MESSAGE =
  '필지 데이터가 없어 건물 기반으로 표시 중입니다.';

export async function loadAppData() {
  try {
    const results = await Promise.allSettled([
      fetch(DATA_PATHS.boundary).then(toJson),
      fetch(DATA_PATHS.buildings).then(toJson),
      fetch(DATA_PATHS.buildingSummary).then(toText),
      fetch(DATA_PATHS.parcels).then(toJson),
      fetch(DATA_PATHS.parcelSummary).then(toText),
      fetch(DATA_PATHS.urbanFacilities).then(toJson),
      fetch(DATA_PATHS.classificationDiagnosis).then(toText),
      fetch(DATA_PATHS.unclassifiedDiagnosis).then(toText),
    ]);

    const [
      boundaryResult,
      buildingsResult,
      buildingSummaryResult,
      parcelsResult,
      parcelSummaryResult,
      urbanFacilitiesResult,
      classificationDiagnosisResult,
      unclassifiedDiagnosisResult,
    ] = results;

    const usingFallback =
      boundaryResult.status !== 'fulfilled' ||
      buildingsResult.status !== 'fulfilled' ||
      buildingSummaryResult.status !== 'fulfilled';

    const parcelDataAvailable =
      parcelsResult.status === 'fulfilled' && Array.isArray(parcelsResult.value?.features);

    return {
      boundary:
        boundaryResult.status === 'fulfilled' ? boundaryResult.value : SAMPLE_DATA.boundary,
      buildings:
        buildingsResult.status === 'fulfilled' ? buildingsResult.value : SAMPLE_DATA.buildings,
      buildingSummaryRows:
        buildingSummaryResult.status === 'fulfilled'
          ? parseSummaryCsv(buildingSummaryResult.value)
          : parseSummaryCsv(SAMPLE_DATA.buildingSummaryCsv),
      parcels: parcelsResult.status === 'fulfilled' ? parcelsResult.value : SAMPLE_DATA.parcels,
      parcelSummaryRows:
        parcelSummaryResult.status === 'fulfilled'
          ? parseSummaryCsv(parcelSummaryResult.value)
          : parseSummaryCsv(SAMPLE_DATA.parcelSummaryCsv),
      urbanFacilities:
        urbanFacilitiesResult.status === 'fulfilled' ? urbanFacilitiesResult.value : null,
      classificationDiagnosis:
        classificationDiagnosisResult.status === 'fulfilled'
          ? parseDiagnosisCsv(classificationDiagnosisResult.value)
          : [],
      unclassifiedDiagnosis:
        unclassifiedDiagnosisResult.status === 'fulfilled'
          ? parseDiagnosisCsv(unclassifiedDiagnosisResult.value)
          : [],
      usingFallback,
      loadErrorMessage: usingFallback ? DEFAULT_LOAD_ERROR_MESSAGE : '',
      parcelDataAvailable,
      parcelFallbackMessage: parcelDataAvailable ? '' : DEFAULT_PARCEL_FALLBACK_MESSAGE,
    };
  } catch (error) {
    return {
      boundary: SAMPLE_DATA.boundary,
      buildings: SAMPLE_DATA.buildings,
      buildingSummaryRows: parseSummaryCsv(SAMPLE_DATA.buildingSummaryCsv),
      parcels: SAMPLE_DATA.parcels,
      parcelSummaryRows: parseSummaryCsv(SAMPLE_DATA.parcelSummaryCsv),
      urbanFacilities: null,
      classificationDiagnosis: [],
      unclassifiedDiagnosis: [],
      usingFallback: true,
      loadErrorMessage: DEFAULT_LOAD_ERROR_MESSAGE,
      parcelDataAvailable: true,
      parcelFallbackMessage: '',
      error,
    };
  }
}

async function toJson(response) {
  if (!response.ok) {
    throw new Error(`Failed to load ${response.url}`);
  }
  return response.json();
}

async function toText(response) {
  if (!response.ok) {
    throw new Error(`Failed to load ${response.url}`);
  }
  return response.text();
}

export function parseSummaryCsv(csvText) {
  const [headerLine, ...lines] = (csvText || '').trim().split(/\r?\n/);
  if (!headerLine) {
    return [];
  }

  const headers = headerLine.split(',').map((item) => item.trim());
  return lines
    .filter(Boolean)
    .map((line) => {
      const values = line.split(',').map((item) => item.trim());
      const row = Object.fromEntries(headers.map((header, index) => [header, values[index]]));
      return {
        landuse_group: row.landuse_group || '기타',
        area_m2: Number(row.area_m2 || 0),
        ratio: Number(row.ratio || 0),
        building_count: Number(row.building_count || row.count || 0),
        parcel_count:
          row.parcel_count === undefined || row.parcel_count === ''
            ? null
            : Number(row.parcel_count),
      };
    });
}

export function parseDiagnosisCsv(csvText) {
  const [headerLine, ...lines] = (csvText || '').trim().split(/\r?\n/);
  if (!headerLine) {
    return [];
  }

  const headers = headerLine.split(',').map((item) => item.trim());
  return lines
    .filter(Boolean)
    .map((line) => {
      const values = line.split(',').map((item) => item.trim());
      const row = Object.fromEntries(headers.map((header, index) => [header, values[index]]));
      return row;
    });
}

export function normalizeBuildings(geojson) {
  return (geojson?.features || []).map((feature, index) => ({
    ...feature,
    properties: {
      ...feature.properties,
      id: feature?.properties?.id || `BLDG_${String(index + 1).padStart(6, '0')}`,
      landuse_group: feature?.properties?.landuse_group || '기타',
      main_use: feature?.properties?.main_use || '정보 없음',
      area_m2: Number(feature?.properties?.area_m2 || 0),
      address: feature?.properties?.address || '주소 정보 없음',
    },
  }));
}

export function normalizeParcels(geojson) {
  return (geojson?.features || []).map((feature, index) => {
    const fallbackId = `PCL_${String(index + 1).padStart(6, '0')}`;
    const rawPriority = feature?.properties?.source_priority || '7_unclassified';
    const normalizedPriority =
      rawPriority === '4_nearest_building'
        ? '5_nearest_building'
        : rawPriority === '5_unclassified'
          ? '7_unclassified'
          : rawPriority;
    return {
      ...feature,
      properties: {
        ...feature.properties,
        id: feature?.properties?.id || fallbackId,
        parcel_id: feature?.properties?.parcel_id || feature?.properties?.id || fallbackId,
        landuse_group: feature?.properties?.landuse_group || '미분류',
        legal_basis: feature?.properties?.legal_basis || '미분류',
        source_priority: normalizedPriority,
        dominant_building_use: feature?.properties?.dominant_building_use || '',
        jimok: feature?.properties?.jimok || '',
        urban_facility: feature?.properties?.urban_facility || '',
        zoning: feature?.properties?.zoning || '',
        area_m2: Number(feature?.properties?.area_m2 || 0),
        building_count: Number(feature?.properties?.building_count || 0),
        match_status: feature?.properties?.match_status || '미분류',
        confidence: feature?.properties?.confidence || 'low',
        diagnosis:
          feature?.properties?.diagnosis ||
          feature?.properties?.reason ||
          feature?.properties?.match_status ||
          '추가 근거가 부족해 미분류로 남아 있습니다.',
      },
    };
  });
}

export function summarizeBuildings(buildings, visibleLanduses) {
  const filtered = buildings.filter((feature) =>
    visibleLanduses.includes(feature.properties.landuse_group),
  );
  const totalArea = filtered.reduce(
    (sum, feature) => sum + Number(feature.properties.area_m2 || 0),
    0,
  );
  const totalCount = filtered.length;

  const grouped = filtered.reduce((accumulator, feature) => {
    const key = feature.properties.landuse_group || '기타';
    if (!accumulator[key]) {
      accumulator[key] = {
        landuse_group: key,
        area_m2: 0,
        building_count: 0,
        parcel_count: null,
        ratio: 0,
      };
    }

    accumulator[key].area_m2 += Number(feature.properties.area_m2 || 0);
    accumulator[key].building_count += 1;
    return accumulator;
  }, {});

  return {
    totalArea,
    totalCount,
    countLabel: '건축물 수',
    rows: finalizeSummaryRows(Object.values(grouped), totalArea),
  };
}

export function summarizeParcels(parcels, visibleLanduses, summaryScope = 'exclude_transport_water') {
  const filtered = filterParcelsByScope(
    parcels.filter((feature) => visibleLanduses.includes(feature.properties.landuse_group)),
    summaryScope,
  );
  const totalArea = filtered.reduce(
    (sum, feature) => sum + Number(feature.properties.area_m2 || 0),
    0,
  );
  const totalCount = filtered.length;

  const grouped = filtered.reduce((accumulator, feature) => {
    const key = feature.properties.landuse_group || '미분류';
    if (!accumulator[key]) {
      accumulator[key] = {
        landuse_group: key,
        area_m2: 0,
        building_count: 0,
        parcel_count: 0,
        ratio: 0,
      };
    }

    accumulator[key].area_m2 += Number(feature.properties.area_m2 || 0);
    accumulator[key].building_count += Number(feature.properties.building_count || 0);
    accumulator[key].parcel_count += 1;
    return accumulator;
  }, {});

  return {
    totalArea,
    totalCount,
    countLabel: '필지 수',
    rows: finalizeSummaryRows(Object.values(grouped), totalArea),
  };
}

export function filterParcelsByScope(parcels, summaryScope) {
  return parcels.filter((feature) => shouldIncludeParcelForSummary(feature, summaryScope));
}

export function summaryRowsToDisplayRows(summaryRows, summaryMode = 'building') {
  const totalArea = summaryRows.reduce((sum, row) => sum + Number(row.area_m2 || 0), 0);
  const totalCount = summaryRows.reduce((sum, row) => {
    const nextValue =
      summaryMode === 'parcel' ? Number(row.parcel_count || 0) : Number(row.building_count || 0);
    return sum + nextValue;
  }, 0);

  return {
    totalArea,
    totalCount,
    countLabel: summaryMode === 'parcel' ? '필지 수' : '건축물 수',
    rows: finalizeSummaryRows(summaryRows, totalArea),
  };
}

function finalizeSummaryRows(rows, totalArea) {
  return rows
    .filter((row) => Number(row.area_m2 || 0) > 0)
    .map((row) => ({
      ...row,
      area_m2: Number(row.area_m2 || 0),
      building_count: Number(row.building_count || 0),
      parcel_count:
        row.parcel_count === null || row.parcel_count === undefined
          ? null
          : Number(row.parcel_count),
      ratio: totalArea > 0 ? (Number(row.area_m2 || 0) / totalArea) * 100 : 0,
    }))
    .sort((a, b) => b.area_m2 - a.area_m2);
}

export function mergeParcelCounts(rows, summaryRows) {
  const parcelCountMap = new Map(
    summaryRows.map((row) => [row.landuse_group, row.parcel_count ?? null]),
  );
  return rows.map((row) => ({
    ...row,
    parcel_count: parcelCountMap.has(row.landuse_group)
      ? parcelCountMap.get(row.landuse_group)
      : row.parcel_count ?? null,
  }));
}

function shouldIncludeParcelForSummary(feature, summaryScope) {
  const landuse = feature.properties.landuse_group;
  const sourcePriority = feature.properties.source_priority;

  if (summaryScope === 'exclude_transport') {
    return landuse !== '도로/교통시설';
  }
  if (summaryScope === 'exclude_transport_water') {
    return !['도로/교통시설', '하천/수공간'].includes(landuse);
  }
  if (summaryScope === 'exclude_transport_water_park') {
    return !['도로/교통시설', '하천/수공간', '공원/녹지'].includes(landuse);
  }
  if (summaryScope === 'building_only') {
    return sourcePriority === '1_building_use';
  }
  if (summaryScope === 'include_supporting') {
    return ['1_building_use', '2_jimok', '3_urban_facility', '4_zoning_support', '5_nearest_building'].includes(
      sourcePriority,
    );
  }
  return true;
}

export function buildUnclassifiedNotice(rows) {
  const unclassified = rows.find((row) => row.landuse_group === '미분류');
  if (!unclassified || unclassified.ratio < 10) {
    return '';
  }
  return '미분류는 건축물 용도, 지목, 도시계획시설 정보로도 대표 용도를 판단하기 어려운 필지입니다.';
}

export function getBoundaryFeatureCollection(boundaryGeojson) {
  if (!boundaryGeojson) {
    return SAMPLE_DATA.boundary;
  }
  if (boundaryGeojson.type === 'FeatureCollection') {
    return boundaryGeojson;
  }
  if (boundaryGeojson.type === 'Feature') {
    return { type: 'FeatureCollection', features: [boundaryGeojson] };
  }
  return SAMPLE_DATA.boundary;
}

export function getBoundsFromGeoJson(geojson) {
  const coordinates = [];
  for (const feature of geojson?.features || []) {
    collectCoordinates(feature.geometry, coordinates);
  }
  if (coordinates.length === 0) {
    return [127.073, 37.474, 127.142, 37.534];
  }

  const longitudes = coordinates.map((coord) => coord[0]);
  const latitudes = coordinates.map((coord) => coord[1]);
  return [
    Math.min(...longitudes),
    Math.min(...latitudes),
    Math.max(...longitudes),
    Math.max(...latitudes),
  ];
}

function collectCoordinates(geometry, accumulator) {
  if (!geometry) {
    return;
  }
  if (geometry.type === 'Polygon') {
    geometry.coordinates[0].forEach((coord) => accumulator.push(coord));
    return;
  }
  if (geometry.type === 'MultiPolygon') {
    geometry.coordinates.forEach((polygon) => {
      polygon[0].forEach((coord) => accumulator.push(coord));
    });
  }
}
