export const LEGAL_BASIS_LABELS = {
  '건축물 용도 기준': '건축물 교차면적과 대표 주용도를 기준으로 분류한 결과입니다.',
  '지목 기준': '지목 속성과 공공용지 성격을 기준으로 보조 분류한 결과입니다.',
  '도시계획 시설 기준': '도시계획 시설정보와의 중첩을 기준으로 보조 분류한 결과입니다.',
  '용도지역 보조 기준': '용도지역/지구 정보가 있을 때 참고용으로 반영한 결과입니다.',
  '근접 건축물 보조 매칭': '2m 이내의 인접 건축물을 찾아 보조 추정한 결과입니다.',
  '건물없음': '건축물 및 보조 분류 근거가 없어 비건축 배경 필지로 남아 있는 상태입니다.',
  미분류: '건축물, 지목, 도시계획 시설, 용도지역 정보만으로는 대표 용도를 판단하기 어려운 상태입니다.',
};

export const SOURCE_PRIORITY_ORDER = [
  '1_building_use',
  '2_jimok',
  '3_urban_facility',
  '4_zoning_support',
  '5_nearest_building',
  '6_background_no_building',
  '7_unclassified',
];

export const SOURCE_PRIORITY_LABELS = {
  '1_building_use': '1순위 건축물 용도',
  '2_jimok': '2순위 지목',
  '3_urban_facility': '3순위 도시계획 시설',
  '4_zoning_support': '4순위 용도지역 보조',
  '5_nearest_building': '5순위 근접 건축물 보조',
  '6_background_no_building': '6순위 건물없음',
  '7_unclassified': '7순위 미분류',
};

