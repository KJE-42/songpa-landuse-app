import { useMemo } from 'react';
import LanduseChart from './LanduseChart';
import { formatArea, formatCount, formatOptionalCount, formatPercent } from '../utils/format';

function ReportModal({
  open,
  onClose,
  rows,
  totalArea,
  totalCount,
  countLabel,
  summaryMode,
  summaryScope,
}) {
  const topFive = useMemo(() => rows.slice(0, 5), [rows]);

  if (!open) {
    return null;
  }

  const interpretation = buildInterpretation(rows, totalArea, totalCount, countLabel);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="panel-header">
          <div>
            <p className="panel-header__eyebrow">분석 보고서</p>
            <h2>송파구 토지이용 요약</h2>
          </div>
          <div className="modal__actions">
            <button type="button" className="button button--ghost" onClick={() => window.print()}>
              인쇄
            </button>
            <button type="button" className="button button--ghost" onClick={() => downloadCsv(rows)}>
              CSV 다운로드
            </button>
            <button type="button" className="button button--ghost" onClick={onClose}>
              닫기
            </button>
          </div>
        </div>

        <section className="report-section">
          <h3>분석 개요</h3>
          <p>
            현재 지도에 표시 중인 용도만을 기준으로 송파구 토지이용 분포를 요약한 결과입니다.
            집계 기준은 {summaryMode === 'parcel' ? '필지 기준' : '건물 기준'}이며, 통계 옵션은{' '}
            <strong>{summaryScope}</strong>입니다.
          </p>
        </section>

        <section className="report-grid">
          <article className="report-stat">
            <span>총 {countLabel}</span>
            <strong>{formatCount(totalCount)}건</strong>
          </article>
          <article className="report-stat">
            <span>총 면적</span>
            <strong>{formatArea(totalArea)}㎡</strong>
          </article>
        </section>

        <section className="report-section">
          <h3>용도별 TOP 5</h3>
          <table className="report-table">
            <thead>
              <tr>
                <th>순위</th>
                <th>용도</th>
                <th>면적(㎡)</th>
                <th>구성비(%)</th>
                <th>건축물 수</th>
                <th>필지 수</th>
              </tr>
            </thead>
            <tbody>
              {topFive.map((row, index) => (
                <tr key={row.landuse_group}>
                  <td>{index + 1}</td>
                  <td>{row.landuse_group}</td>
                  <td>{formatArea(row.area_m2)}</td>
                  <td>{formatPercent(row.ratio)}</td>
                  <td>{formatCount(row.building_count)}</td>
                  <td>{formatOptionalCount(row.parcel_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="report-section">
          <LanduseChart rows={rows} countLabel={countLabel} />
        </section>

        <section className="report-section">
          <h3>간단한 해석</h3>
          <p>{interpretation}</p>
        </section>

        <section className="report-section">
          <h3>유의사항</h3>
          <p>
            미분류는 건축물, 지목, 도시계획 시설, 용도지역 정보로도 대표 용도를 판단하기 어려운
            필지입니다. 법적 판단이 필요한 경우에는 원천 공간정보와 건축물대장, 지목, 도시계획
            도면을 함께 확인해야 합니다.
          </p>
        </section>
      </div>
    </div>
  );
}

function buildInterpretation(rows, totalArea, totalCount, countLabel) {
  if (!rows.length || totalArea === 0) {
    return '현재 선택된 조건에서는 분석 가능한 집계 데이터가 없습니다.';
  }

  const top = rows[0];
  const unclassified = rows.find((row) => row.landuse_group === '미분류');
  const unclassifiedMessage = unclassified
    ? ` 미분류 비중은 ${formatPercent(unclassified.ratio)}%로, 추가 지목 또는 용도지역 자료가 있으면 더 줄일 수 있습니다.`
    : '';

  return `${top.landuse_group}이(가) 전체 표시 면적의 ${formatPercent(
    top.ratio,
  )}%를 차지해 가장 큰 비중을 보입니다. 현재 집계 대상은 총 ${formatCount(
    totalCount,
  )}건의 ${countLabel}이며 총 면적은 ${formatArea(totalArea)}㎡입니다.${unclassifiedMessage}`;
}

function downloadCsv(rows) {
  const header = 'landuse_group,area_m2,ratio_percent,building_count,parcel_count';
  const lines = rows.map(
    (row) =>
      `${row.landuse_group},${row.area_m2.toFixed(1)},${row.ratio.toFixed(1)},${row.building_count},${row.parcel_count ?? ''}`,
  );
  const blob = new Blob([[header, ...lines].join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'songpa_landuse_report.csv';
  link.click();
  URL.revokeObjectURL(url);
}

export default ReportModal;

