import { useState } from 'react';
import { LANDUSE_ORDER, getLanduseColor } from '../utils/colors';

function LayerPanel({
  showBoundary,
  showBuildingsLayer,
  onToggleBoundary,
  onToggleBuildingsLayer,
  visibleLanduses,
  onToggleLanduse,
  onSelectAll,
  onClearAll,
}) {
  const [isOpen, setIsOpen] = useState(true);
  const [activeTab, setActiveTab] = useState('general');

  return (
    <div className={`layer-panel ${isOpen ? 'is-open' : 'is-collapsed'}`}>
      <button
        type="button"
        className="layer-panel__toggle"
        onClick={() => setIsOpen((current) => !current)}
      >
        {isOpen ? '레이어 접기' : '레이어 펼치기'}
      </button>

      {isOpen ? (
        <div className="layer-panel__body">
          <div className="layer-panel__tabs">
            <button
              type="button"
              className={`layer-panel__tab ${activeTab === 'general' ? 'is-active' : ''}`}
              onClick={() => setActiveTab('general')}
            >
              일반레이어
            </button>
            <button
              type="button"
              className={`layer-panel__tab ${activeTab === 'custom' ? 'is-active' : ''}`}
              onClick={() => setActiveTab('custom')}
            >
              사용자레이어
            </button>
          </div>

          {activeTab === 'general' ? (
            <>
              <div className="panel-header panel-header--compact">
                <div>
                  <p className="panel-header__eyebrow">기본 레이어</p>
                  <h3>경계 및 참고 레이어</h3>
                </div>
              </div>

              <div className="layer-panel__list layer-panel__list--compact">
                <label className="checkbox-row">
                  <input type="checkbox" checked={showBoundary} onChange={onToggleBoundary} />
                  <span className="boundary-chip" />
                  <span>송파구 경계</span>
                </label>

                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={showBuildingsLayer}
                    onChange={onToggleBuildingsLayer}
                  />
                  <span className="legend-chip legend-chip--outline" />
                  <span>건물 보조 레이어</span>
                </label>
              </div>
            </>
          ) : (
            <>
              <div className="panel-header panel-header--compact">
                <div>
                  <p className="panel-header__eyebrow">사용자 레이어</p>
                  <h3>용도 표시 항목</h3>
                </div>
              </div>

              <div className="layer-panel__actions">
                <button type="button" className="button button--ghost" onClick={onSelectAll}>
                  전체 선택
                </button>
                <button type="button" className="button button--ghost" onClick={onClearAll}>
                  전체 해제
                </button>
              </div>

              <div className="layer-panel__list">
                {LANDUSE_ORDER.map((landuse) => {
                  const checked = visibleLanduses.includes(landuse);
                  return (
                    <label key={landuse} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => onToggleLanduse(landuse)}
                      />
                      <span
                        className="legend-chip"
                        style={{
                          backgroundColor: `rgb(${getLanduseColor(landuse).join(',')})`,
                        }}
                      />
                      <span>{landuse}</span>
                    </label>
                  );
                })}
              </div>
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}

export default LayerPanel;

