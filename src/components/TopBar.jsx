import { formatArea, formatCount } from '../utils/format';

function TopBar({ totalCount, totalArea, countLabel, onOpenReport }) {
  return (
    <header className="topbar">
      <div className="topbar__title">
        <p className="topbar__eyebrow">Songpa GIS Analysis</p>
        <h1>토지이용</h1>
        <span className="topbar__subtitle">송파구 건축물 용도 기반 토지이용 분석</span>
      </div>

      <div className="topbar__actions">
        <div className="topbar__metric">
          <span>총 {countLabel}</span>
          <strong>{formatCount(totalCount)}건</strong>
        </div>
        <div className="topbar__metric">
          <span>총 면적</span>
          <strong>{formatArea(totalArea)}㎡</strong>
        </div>
        <button type="button" className="button button--primary" onClick={onOpenReport}>
          보고서
        </button>
      </div>
    </header>
  );
}

export default TopBar;

