import LanduseChart from './LanduseChart';
import { getLanduseColor } from '../utils/colors';
import { formatArea, formatCount, formatOptionalCount, formatPercent } from '../utils/format';

function LanduseTable({
  rows,
  summaryMode,
  requestedSummaryMode,
  summaryScope,
  summaryScopeOptions,
  onChangeSummaryMode,
  onChangeSummaryScope,
  parcelModeEnabled,
  focusedLanduse,
  onSelectLanduse,
  onResetFocus,
  usingFallback,
  isUsingSummaryFallback,
  loadErrorMessage,
  parcelFallbackMessage,
  unclassifiedNotice,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar__hero">
        <p className="sidebar__hero-label">분석 주제</p>
        <h2>토지이용</h2>
        <span>송파구 건축물 용도 기반 토지이용 분석</span>
      </div>

      <div className="panel-header panel-header--table">
        <div>
          <p className="panel-header__eyebrow">토지이용 현황</p>
          <h3>토지이용 현황표</h3>
        </div>
        <button type="button" className="button button--ghost" onClick={onResetFocus}>
          전체 보기
        </button>
      </div>

      <div className="mode-toggle" role="tablist" aria-label="집계 기준 선택">
        <button
          type="button"
          className={`mode-toggle__button ${summaryMode === 'parcel' ? 'is-active' : ''}`}
          onClick={() => onChangeSummaryMode('parcel')}
          disabled={!parcelModeEnabled}
        >
          필지 기준
        </button>
        <button
          type="button"
          className={`mode-toggle__button ${summaryMode === 'building' ? 'is-active' : ''}`}
          onClick={() => onChangeSummaryMode('building')}
        >
          건물 기준
        </button>
      </div>

      <div className="summary-scope">
        <label htmlFor="summary-scope-select">통계 계산 옵션</label>
        <select
          id="summary-scope-select"
          value={summaryScope}
          onChange={(event) => onChangeSummaryScope(event.target.value)}
          disabled={summaryMode !== 'parcel'}
        >
          {summaryScopeOptions.map((option) => (
            <option key={option.key} value={option.key}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {(usingFallback || isUsingSummaryFallback || parcelFallbackMessage) && (
        <div className="notice">
          <strong>안내</strong>
          <p>
            {usingFallback
              ? loadErrorMessage || '실제 데이터 로딩에 실패해 샘플 데이터로 구성했습니다.'
              : parcelFallbackMessage ||
                (requestedSummaryMode === 'parcel' && summaryMode === 'building'
                  ? '필지 데이터가 없어 건물 기준 집계로 전환했습니다.'
                  : '공간 데이터가 없어 CSV 요약값을 기준으로 표시 중입니다.')}
          </p>
        </div>
      )}

      {unclassifiedNotice ? (
        <div className="notice notice--subtle">
          <strong>미분류 안내</strong>
          <p>{unclassifiedNotice}</p>
        </div>
      ) : null}

      <div className="table-wrap">
        <table className="landuse-table">
          <thead>
            <tr>
              <th>범례</th>
              <th>구분</th>
              <th>면적(㎡)</th>
              <th>구성비(%)</th>
              <th>건축물 수</th>
              <th>필지 수</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan="6" className="table-empty">
                  표시 가능한 데이터가 없습니다.
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const isActive = focusedLanduse === row.landuse_group;
                return (
                  <tr
                    key={row.landuse_group}
                    className={isActive ? 'is-active' : ''}
                    onClick={() => onSelectLanduse(row.landuse_group)}
                  >
                    <td>
                      <span
                        className="legend-chip"
                        style={{
                          backgroundColor: `rgb(${getLanduseColor(row.landuse_group).join(',')})`,
                        }}
                      />
                    </td>
                    <td>{row.landuse_group}</td>
                    <td>{formatArea(row.area_m2)}</td>
                    <td>{formatPercent(row.ratio)}</td>
                    <td>{formatCount(row.building_count)}</td>
                    <td>{formatOptionalCount(row.parcel_count)}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <LanduseChart rows={rows} countLabel={summaryMode === 'parcel' ? '필지 수' : '건축물 수'} />
    </aside>
  );
}

export default LanduseTable;

