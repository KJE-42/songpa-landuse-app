export const LANDUSE_ORDER = [
  '단독주택',
  '공동주택',
  '근린생활시설',
  '업무시설',
  '판매시설',
  '교육연구시설',
  '의료/노유자시설',
  '운동시설',
  '숙박시설',
  '위락시설',
  '공원/녹지',
  '하천/수공간',
  '학교/공공시설',
  '도로/교통시설',
  '건물없음',
  '매칭 실패 의심',
  '미분류',
  '기타',
];

const HEX_COLORS = {
  단독주택: '#FFD43B',
  공동주택: '#1E88E5',
  근린생활시설: '#00C853',
  업무시설: '#1565C0',
  판매시설: '#F4511E',
  교육연구시설: '#00BCD4',
  '의료/노유자시설': '#B39DDB',
  운동시설: '#90CAF9',
  숙박시설: '#C62828',
  위락시설: '#8E24AA',
  '공원/녹지': '#8BC34A',
  '하천/수공간': '#4FC3F7',
  '학교/공공시설': '#7CB342',
  '도로/교통시설': '#ECEFF1',
  건물없음: '#F5F5F5',
  '매칭 실패 의심': '#CFD8DC',
  미분류: '#EEEEEE',
  기타: '#9E9E9E',
};

function hexToRgb(hex) {
  const normalized = hex.replace('#', '');
  const value = parseInt(normalized, 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

export const LANDUSE_COLORS = Object.fromEntries(
  Object.entries(HEX_COLORS).map(([key, value]) => [key, hexToRgb(value)]),
);

export const DEFAULT_LANDUSE_COLOR = LANDUSE_COLORS.기타;

export function getLanduseColor(landuse) {
  return LANDUSE_COLORS[landuse] || DEFAULT_LANDUSE_COLOR;
}

export function getLanduseColorHex(landuse) {
  return HEX_COLORS[landuse] || HEX_COLORS.기타;
}

export function isBackgroundLikeLanduse(landuse) {
  return ['도로/교통시설', '공원/녹지', '하천/수공간', '건물없음'].includes(landuse);
}

