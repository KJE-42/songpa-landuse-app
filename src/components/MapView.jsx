import { useEffect, useMemo, useRef, useState } from 'react';
import DeckGL from '@deck.gl/react';
import { FlyToInterpolator } from '@deck.gl/core';
import { GeoJsonLayer, PolygonLayer } from '@deck.gl/layers';
import { Map } from 'react-map-gl/maplibre';
import { getLanduseColor, isBackgroundLikeLanduse } from '../utils/colors';
import { BASEMAP_OPTIONS, BASEMAPS, DEFAULT_BASEMAP_KEY } from '../utils/basemaps';
import { SOURCE_PRIORITY_LABELS } from '../utils/legalLanduseRules';

function MapView({
  buildings,
  parcels,
  boundary,
  showBoundary,
  showBuildingsLayer,
  focusedLanduse,
  hoveredBuilding,
  selectedFeature,
  useParcelView,
  viewState,
  parcelOpacity,
  onParcelOpacityChange,
  onViewStateChange,
  onHoverBuilding,
  onSelectFeature,
  onMoveToSongpa,
  onMoveToSeoul,
}) {
  const [basemapKey, setBasemapKey] = useState(DEFAULT_BASEMAP_KEY);
  const mapShellRef = useRef(null);
  const scaleLabel = useMemo(() => getScaleLabel(viewState.zoom), [viewState.zoom]);
  const activeBasemap = BASEMAPS[basemapKey] || BASEMAPS[DEFAULT_BASEMAP_KEY];

  useEffect(() => {
    if (showBoundary && isLikelyBoundingBox(boundary)) {
      console.warn(
        '송파구 경계 데이터가 실제 행정경계가 아니라 bounding box일 가능성이 있습니다.',
      );
    }
  }, [boundary, showBoundary]);

  useEffect(() => {
    const element = mapShellRef.current;
    if (!element) {
      return undefined;
    }

    const handleWheel = (event) => {
      event.stopPropagation();
    };

    element.addEventListener('wheel', handleWheel, { passive: true });
    return () => {
      element.removeEventListener('wheel', handleWheel);
    };
  }, []);

  const layers = useMemo(() => {
    const parcelAlpha = Math.round((parcelOpacity / 100) * 255);
    const unfocusedAlpha = Math.max(48, Math.round(parcelAlpha * 0.38));
    const backgroundAlpha = Math.max(44, Math.round(parcelAlpha * 0.32));

    const parcelLayer = new GeoJsonLayer({
      id: 'songpa-parcels',
      data: useParcelView
        ? { type: 'FeatureCollection', features: parcels }
        : { type: 'FeatureCollection', features: [] },
      pickable: true,
      stroked: true,
      filled: true,
      lineWidthMinPixels: 0.5,
      getLineColor: (feature) => {
        const isSelected =
          selectedFeature?.kind === 'parcel' &&
          selectedFeature.feature?.properties?.parcel_id === feature.properties.parcel_id;
        return isSelected ? [33, 33, 33, 255] : [255, 255, 255, 180];
      },
      getLineWidth: (feature) => {
        const isSelected =
          selectedFeature?.kind === 'parcel' &&
          selectedFeature.feature?.properties?.parcel_id === feature.properties.parcel_id;
        return isSelected ? 1.3 : 0.55;
      },
      getFillColor: (feature) => {
        const baseColor = getLanduseColor(feature.properties.landuse_group);
        const isFocused = !focusedLanduse || focusedLanduse === feature.properties.landuse_group;
        const isSelected =
          selectedFeature?.kind === 'parcel' &&
          selectedFeature.feature?.properties?.parcel_id === feature.properties.parcel_id;

        let alpha = isBackgroundLikeLanduse(feature.properties.landuse_group)
          ? backgroundAlpha
          : isFocused
            ? parcelAlpha
            : unfocusedAlpha;

        if (isSelected) {
          alpha = 255;
        }

        return [...baseColor, alpha];
      },
      onClick: ({ object }) => onSelectFeature(object ? { kind: 'parcel', feature: object } : null),
      updateTriggers: {
        getFillColor: [focusedLanduse, parcelOpacity, selectedFeature],
        getLineColor: [selectedFeature],
        getLineWidth: [selectedFeature],
      },
    });

    const buildingsLayer = new PolygonLayer({
      id: 'songpa-buildings',
      data: buildings,
      pickable: true,
      autoHighlight: false,
      stroked: true,
      filled: true,
      extruded: false,
      visible: (!useParcelView || showBuildingsLayer) && viewState.zoom >= 16,
      lineWidthUnits: 'pixels',
      getLineWidth: (feature) => {
        const isSelected =
          selectedFeature?.kind === 'building' &&
          selectedFeature.feature?.properties?.id === feature.properties.id;
        const isHovered = hoveredBuilding?.properties?.id === feature.properties.id;
        return isSelected || isHovered ? 2 : 1;
      },
      getLineColor: (feature) => {
        const isSelected =
          selectedFeature?.kind === 'building' &&
          selectedFeature.feature?.properties?.id === feature.properties.id;
        const isHovered = hoveredBuilding?.properties?.id === feature.properties.id;
        if (isSelected) {
          return [24, 39, 57, 255];
        }
        if (isHovered) {
          return [255, 255, 255, 255];
        }
        return [70, 70, 70, 180];
      },
      getPolygon: getPolygonCoordinates,
      getFillColor: (feature) => {
        const baseColor = getLanduseColor(feature.properties.landuse_group);
        const isSelected =
          selectedFeature?.kind === 'building' &&
          selectedFeature.feature?.properties?.id === feature.properties.id;
        const isHovered = hoveredBuilding?.properties?.id === feature.properties.id;
        const opacity = isSelected ? 235 : isHovered ? 205 : 128;
        return [...baseColor, opacity];
      },
      onHover: onHoverBuilding,
      onClick: ({ object }) => onSelectFeature(object ? { kind: 'building', feature: object } : null),
      updateTriggers: {
        getFillColor: [hoveredBuilding, selectedFeature],
        getLineWidth: [hoveredBuilding, selectedFeature],
        getLineColor: [hoveredBuilding, selectedFeature],
      },
    });

    const boundaryLayer = new GeoJsonLayer({
      id: 'songpa-boundary',
      data: showBoundary ? boundary : { type: 'FeatureCollection', features: [] },
      stroked: true,
      filled: false,
      lineWidthMinPixels: 3,
      lineWidthUnits: 'pixels',
      getLineColor: [230, 0, 0, 245],
      getLineWidth: 3.2,
      lineDashJustified: true,
      getLineDashArray: [6, 4],
      pickable: false,
    });

    return [parcelLayer, buildingsLayer, boundaryLayer];
  }, [
    boundary,
    buildings,
    focusedLanduse,
    hoveredBuilding,
    onHoverBuilding,
    onSelectFeature,
    parcelOpacity,
    parcels,
    selectedFeature,
    showBoundary,
    showBuildingsLayer,
    useParcelView,
    viewState.zoom,
  ]);

  function zoomBy(delta) {
    onViewStateChange({
      ...viewState,
      zoom: Math.max(9.5, Math.min(17, viewState.zoom + delta)),
    });
  }

  return (
    <div className="map-shell" ref={mapShellRef}>
      <DeckGL
        layers={layers}
        controller
        viewState={{
          ...viewState,
          transitionDuration: 0,
          transitionInterpolator: new FlyToInterpolator(),
        }}
        onViewStateChange={({ viewState: nextViewState }) => onViewStateChange(nextViewState)}
      >
        <Map reuseMaps mapStyle={activeBasemap.style} attributionControl />
      </DeckGL>

      <div className="basemap-switcher">
        <label htmlFor="basemap-select" className="basemap-switcher__label">
          배경지도
        </label>
        <select
          id="basemap-select"
          className="basemap-switcher__select"
          value={basemapKey}
          onChange={(event) => setBasemapKey(event.target.value)}
        >
          {BASEMAP_OPTIONS.map((option) => (
            <option key={option.key} value={option.key}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="map-opacity-control">
        <label htmlFor="parcel-opacity-range">토지이용 색상 투명도</label>
        <div className="map-opacity-control__row">
          <input
            id="parcel-opacity-range"
            type="range"
            min="30"
            max="100"
            step="5"
            value={parcelOpacity}
            onChange={(event) => onParcelOpacityChange(Number(event.target.value))}
          />
          <strong>{parcelOpacity}%</strong>
        </div>
      </div>

      <div className="map-view-actions">
        <button type="button" className="map-view-button" onClick={onMoveToSongpa}>
          송파구로 이동
        </button>
        <button type="button" className="map-view-button" onClick={onMoveToSeoul}>
          서울 전체 보기
        </button>
      </div>

      <div className="map-controls">
        <button type="button" className="map-control-button" onClick={() => zoomBy(1)}>
          +
        </button>
        <button type="button" className="map-control-button" onClick={() => zoomBy(-1)}>
          -
        </button>
      </div>

      <div className="map-scale">
        <span className="map-scale__bar" />
        <span className="map-scale__label">{scaleLabel}</span>
      </div>

      {selectedFeature ? (
        <div className="map-popup">
          {selectedFeature.kind === 'parcel' ? (
            <ParcelPopup feature={selectedFeature.feature} onClose={() => onSelectFeature(null)} />
          ) : (
            <BuildingPopup
              feature={selectedFeature.feature}
              onClose={() => onSelectFeature(null)}
            />
          )}
        </div>
      ) : null}
    </div>
  );
}

function ParcelPopup({ feature, onClose }) {
  const properties = feature.properties;
  return (
    <>
      <div className="map-popup__header">
        <strong>필지 {properties.parcel_id}</strong>
        <button type="button" className="popup-close" onClick={onClose}>
          닫기
        </button>
      </div>
      <dl>
        <div>
          <dt>필지 ID</dt>
          <dd>{properties.parcel_id || '-'}</dd>
        </div>
        <div>
          <dt>대표 용도</dt>
          <dd>{properties.landuse_group}</dd>
        </div>
        <div>
          <dt>지목</dt>
          <dd>{properties.jimok || '-'}</dd>
        </div>
        <div>
          <dt>도시계획 시설</dt>
          <dd>{properties.urban_facility || '-'}</dd>
        </div>
        <div>
          <dt>용도지역/지구</dt>
          <dd>{properties.zoning || '-'}</dd>
        </div>
        <div>
          <dt>건물 대표 주용도</dt>
          <dd>{properties.dominant_building_use || '-'}</dd>
        </div>
        <div>
          <dt>legal_basis</dt>
          <dd>{properties.legal_basis || '-'}</dd>
        </div>
        <div>
          <dt>source_priority</dt>
          <dd>
            {SOURCE_PRIORITY_LABELS[properties.source_priority] ||
              properties.source_priority ||
              '-'}
          </dd>
        </div>
        <div>
          <dt>confidence</dt>
          <dd>{properties.confidence || '-'}</dd>
        </div>
        <div>
          <dt>match_status</dt>
          <dd>{properties.match_status || '-'}</dd>
        </div>
        <div>
          <dt>면적</dt>
          <dd>{formatAreaLabel(properties.area_m2)}</dd>
        </div>
        <div>
          <dt>건축물 수</dt>
          <dd>{Number(properties.building_count || 0).toLocaleString('ko-KR')}건</dd>
        </div>
        <div>
          <dt>진단</dt>
          <dd>{properties.diagnosis || properties.match_status || '추가 진단 정보 없음'}</dd>
        </div>
      </dl>
    </>
  );
}

function BuildingPopup({ feature, onClose }) {
  const properties = feature.properties;
  return (
    <>
      <div className="map-popup__header">
        <strong>{properties.address}</strong>
        <button type="button" className="popup-close" onClick={onClose}>
          닫기
        </button>
      </div>
      <dl>
        <div>
          <dt>원본 주용도</dt>
          <dd>{properties.main_use}</dd>
        </div>
        <div>
          <dt>분석용 용도</dt>
          <dd>{properties.landuse_group}</dd>
        </div>
        <div>
          <dt>면적</dt>
          <dd>{formatAreaLabel(properties.area_m2)}</dd>
        </div>
      </dl>
    </>
  );
}

function formatAreaLabel(value) {
  return `${Number(value || 0).toLocaleString('ko-KR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}㎡`;
}

function getScaleLabel(zoom) {
  if (zoom >= 15) return '100 m';
  if (zoom >= 14) return '200 m';
  if (zoom >= 13) return '500 m';
  if (zoom >= 12) return '1 km';
  return '2 km';
}

function getPolygonCoordinates(feature) {
  if (feature.geometry.type === 'Polygon') return feature.geometry.coordinates[0];
  if (feature.geometry.type === 'MultiPolygon') return feature.geometry.coordinates[0][0];
  return [];
}

function isLikelyBoundingBox(boundaryGeoJson) {
  const feature = boundaryGeoJson?.features?.[0];
  const ring =
    feature?.geometry?.type === 'Polygon'
      ? feature.geometry.coordinates?.[0]
      : feature?.geometry?.type === 'MultiPolygon'
        ? feature.geometry.coordinates?.[0]?.[0]
        : null;

  if (!ring || ring.length !== 5) return false;
  const corners = ring.slice(0, 4);
  const uniqueX = new Set(corners.map((coord) => coord[0]));
  const uniqueY = new Set(corners.map((coord) => coord[1]));
  return uniqueX.size === 2 && uniqueY.size === 2;
}

export default MapView;
