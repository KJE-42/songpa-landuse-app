const areaFormatter = new Intl.NumberFormat('ko-KR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const percentFormatter = new Intl.NumberFormat('ko-KR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const integerFormatter = new Intl.NumberFormat('ko-KR');

export function formatArea(value) {
  return areaFormatter.format(Number(value || 0));
}

export function formatPercent(value) {
  return percentFormatter.format(Number(value || 0));
}

export function formatCount(value) {
  return integerFormatter.format(Number(value || 0));
}

export function formatOptionalCount(value) {
  if (value === '' || value === null || value === undefined || Number.isNaN(Number(value))) {
    return '-';
  }
  return integerFormatter.format(Number(value));
}
