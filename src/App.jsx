import { useEffect, useMemo, useState } from 'react';
import TopBar from './components/TopBar';
import MapView from './components/MapView';
import LanduseTable from './components/LanduseTable';
import LayerPanel from './components/LayerPanel';
import ReportModal from './components/ReportModal';
import { LANDUSE_ORDER } from './utils/colors';
import {
  INITIAL_VISIBLE_LANDUSES,
  SUMMARY_SCOPE_OPTIONS,
  buildUnclassifiedNotice,
  getBoundaryFeatureCollection,
  getBoundsFromGeoJson,
  loadAppData,
  mergeParcelCounts,
  normalizeBuildings,
  normalizeParcels,
  summarizeBuildings,
  summarizeParcels,
  summaryRowsToDisplayRows,
} from './utils/landuse';

const PARCEL_OPACITY_STORAGE_KEY = 'songpa-landuse-parcel-opacity';

const SONGPA_VIEW_STATE = {
  longitude: 127.105,
  latitude: 37.514,
  zoom: 12,
  pitch: 0,
  bearing: 0,
};

const SEOUL_VIEW_STATE = {
  longitude: 127.02,
  latitude: 37.55,
  zoom: 10.2,
  pitch: 0,
  bearing: 0,
};

function App() {
  const [boundary, setBoundary] = useState(getBoundaryFeatureCollection());
  const [buildings, setBuildings] = useState([]);
  const [parcels, setParcels] = useState([]);
  const [buildingSummaryRows, setBuildingSummaryRows] = useState([]);
  const [parcelSummaryRows, setParcelSummaryRows] = useState([]);
  const [usingFallback, setUsingFallback] = useState(false);
  const [loadErrorMessage, setLoadErrorMessage] = useState('');
  const [parcelFallbackMessage, setParcelFallbackMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [showBoundary, setShowBoundary] = useState(true);
  const [showBuildingsLayer, setShowBuildingsLayer] = useState(false);
  const [visibleLanduses, setVisibleLanduses] = useState(INITIAL_VISIBLE_LANDUSES);
  const [focusedLanduse, setFocusedLanduse] = useState(null);
  const [hoveredBuilding, setHoveredBuilding] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [viewState, setViewState] = useState(SONGPA_VIEW_STATE);
  const [summaryMode, setSummaryMode] = useState('parcel');
  const [summaryScope, setSummaryScope] = useState('exclude_transport_water');
  const [parcelOpacity, setParcelOpacity] = useState(() => {
    const stored = window.localStorage.getItem(PARCEL_OPACITY_STORAGE_KEY);
    const numeric = Number(stored);
    return Number.isFinite(numeric) && numeric >= 30 && numeric <= 100 ? numeric : 85;
  });

  useEffect(() => {
    window.localStorage.setItem(PARCEL_OPACITY_STORAGE_KEY, String(parcelOpacity));
  }, [parcelOpacity]);

  useEffect(() => {
    let mounted = true;

    async function initialize() {
      try {
        const data = await loadAppData();
        if (!mounted) {
          return;
        }

        const boundaryCollection = getBoundaryFeatureCollection(data.boundary);
        setBoundary(boundaryCollection);
        setBuildings(normalizeBuildings(data.buildings));
        setParcels(data.parcelDataAvailable ? normalizeParcels(data.parcels) : []);
        setBuildingSummaryRows(data.buildingSummaryRows);
        setParcelSummaryRows(data.parcelSummaryRows);
        setUsingFallback(data.usingFallback);
        setLoadErrorMessage(data.loadErrorMessage || '');
        setParcelFallbackMessage(data.parcelFallbackMessage || '');
        setViewState(createViewStateFromBoundary(boundaryCollection));
      } catch (error) {
        if (!mounted) {
          return;
        }
        setUsingFallback(true);
        setLoadErrorMessage(
          '데이터 파일을 불러오지 못했습니다. public/data 폴더를 확인하세요.',
        );
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    initialize();
    return () => {
      mounted = false;
    };
  }, []);

  const displayedBuildings = useMemo(
    () =>
      buildings.filter((feature) => visibleLanduses.includes(feature.properties.landuse_group)),
    [buildings, visibleLanduses],
  );

  const displayedParcels = useMemo(
    () =>
      parcels.filter((feature) => visibleLanduses.includes(feature.properties.landuse_group)),
    [parcels, visibleLanduses],
  );

  const liveBuildingSummary = useMemo(
    () => summarizeBuildings(buildings, visibleLanduses),
    [buildings, visibleLanduses],
  );

  const liveParcelSummary = useMemo(
    () => summarizeParcels(parcels, visibleLanduses, summaryScope),
    [parcels, summaryScope, visibleLanduses],
  );

  const buildingCsvSummary = useMemo(() => {
    const filteredRows = buildingSummaryRows.filter((row) =>
      visibleLanduses.includes(row.landuse_group),
    );
    return summaryRowsToDisplayRows(filteredRows, 'building');
  }, [buildingSummaryRows, visibleLanduses]);

  const parcelCsvSummary = useMemo(() => {
    const filteredRows = parcelSummaryRows.filter((row) =>
      visibleLanduses.includes(row.landuse_group),
    );
    return summaryRowsToDisplayRows(filteredRows, 'parcel');
  }, [parcelSummaryRows, visibleLanduses]);

  const hasParcelData = parcels.length > 0;
  const effectiveSummaryMode = summaryMode === 'parcel' && hasParcelData ? 'parcel' : 'building';
  const isUsingBuildingSummaryFallback = buildings.length === 0 && buildingCsvSummary.totalCount > 0;
  const isUsingParcelSummaryFallback = parcels.length === 0 && parcelCsvSummary.totalCount > 0;

  const tableData = useMemo(() => {
    if (effectiveSummaryMode === 'parcel') {
      if (parcels.length > 0) {
        return liveParcelSummary;
      }
      return parcelCsvSummary;
    }

    if (isUsingBuildingSummaryFallback) {
      return buildingCsvSummary;
    }

    return {
      ...liveBuildingSummary,
      rows: mergeParcelCounts(liveBuildingSummary.rows, buildingSummaryRows),
    };
  }, [
    buildingCsvSummary,
    buildingSummaryRows,
    effectiveSummaryMode,
    isUsingBuildingSummaryFallback,
    liveBuildingSummary,
    liveParcelSummary,
    parcelCsvSummary,
    parcels.length,
  ]);

  const sidebarNotice =
    effectiveSummaryMode === 'building' && summaryMode === 'parcel' && parcelFallbackMessage
      ? parcelFallbackMessage
      : '';

  const unclassifiedNotice = useMemo(() => buildUnclassifiedNotice(tableData.rows), [tableData.rows]);
  const summaryScopeLabel =
    SUMMARY_SCOPE_OPTIONS.find((option) => option.key === summaryScope)?.label || summaryScope;

  function handleSelectLanduse(landuse) {
    setFocusedLanduse((current) => (current === landuse ? null : landuse));
  }

  function handleToggleLanduse(landuse) {
    setVisibleLanduses((current) => {
      const next = current.includes(landuse)
        ? current.filter((item) => item !== landuse)
        : [...current, landuse].sort(
            (a, b) => LANDUSE_ORDER.indexOf(a) - LANDUSE_ORDER.indexOf(b),
          );

      if (focusedLanduse && !next.includes(focusedLanduse)) {
        setFocusedLanduse(null);
      }

      if (
        selectedFeature &&
        selectedFeature.feature &&
        !next.includes(selectedFeature.feature.properties.landuse_group)
      ) {
        setSelectedFeature(null);
      }

      if (hoveredBuilding && !next.includes(hoveredBuilding.properties.landuse_group)) {
        setHoveredBuilding(null);
      }

      return next;
    });
  }

  function handleSelectAllLanduses() {
    setVisibleLanduses(INITIAL_VISIBLE_LANDUSES);
  }

  function handleClearAllLanduses() {
    setVisibleLanduses([]);
    setFocusedLanduse(null);
    setSelectedFeature(null);
    setHoveredBuilding(null);
  }

  function handleMapHover(info) {
    setHoveredBuilding(info.object || null);
  }

  function handleSelectFeature(selection) {
    setSelectedFeature(selection);
  }

  return (
    <div className="app-shell">
      <TopBar
        totalCount={tableData.totalCount}
        totalArea={tableData.totalArea}
        countLabel={tableData.countLabel}
        onOpenReport={() => setIsReportOpen(true)}
      />

      <main className="dashboard-layout">
        <LanduseTable
          rows={tableData.rows}
          summaryMode={effectiveSummaryMode}
          requestedSummaryMode={summaryMode}
          summaryScope={summaryScope}
          summaryScopeOptions={SUMMARY_SCOPE_OPTIONS}
          onChangeSummaryMode={setSummaryMode}
          onChangeSummaryScope={setSummaryScope}
          parcelModeEnabled={hasParcelData || isUsingParcelSummaryFallback}
          focusedLanduse={focusedLanduse}
          onSelectLanduse={handleSelectLanduse}
          onResetFocus={() => setFocusedLanduse(null)}
          usingFallback={usingFallback}
          isUsingSummaryFallback={isUsingBuildingSummaryFallback || isUsingParcelSummaryFallback}
          loadErrorMessage={loadErrorMessage}
          parcelFallbackMessage={sidebarNotice}
          unclassifiedNotice={unclassifiedNotice}
        />

        <section className="map-layout">
          <div className="map-status">
            {loading
              ? '데이터를 불러오는 중입니다...'
              : visibleLanduses.length === 0
                ? '현재 선택된 용도가 없어 지도가 비어 있습니다.'
                : sidebarNotice
                  ? sidebarNotice
                  : `${visibleLanduses.length}개 용도 그룹을 지도에 표시 중입니다.`}
          </div>

          <MapView
            buildings={displayedBuildings}
            parcels={displayedParcels}
            boundary={boundary}
            showBoundary={showBoundary}
            showBuildingsLayer={showBuildingsLayer}
            focusedLanduse={focusedLanduse}
            hoveredBuilding={hoveredBuilding}
            selectedFeature={selectedFeature}
            useParcelView={hasParcelData}
            viewState={viewState}
            parcelOpacity={parcelOpacity}
            onParcelOpacityChange={setParcelOpacity}
            onViewStateChange={setViewState}
            onHoverBuilding={handleMapHover}
            onSelectFeature={handleSelectFeature}
            onMoveToSongpa={() => setViewState(SONGPA_VIEW_STATE)}
            onMoveToSeoul={() => setViewState(SEOUL_VIEW_STATE)}
          />

          <LayerPanel
            showBoundary={showBoundary}
            showBuildingsLayer={showBuildingsLayer}
            onToggleBoundary={() => setShowBoundary((current) => !current)}
            onToggleBuildingsLayer={() => setShowBuildingsLayer((current) => !current)}
            visibleLanduses={visibleLanduses}
            onToggleLanduse={handleToggleLanduse}
            onSelectAll={handleSelectAllLanduses}
            onClearAll={handleClearAllLanduses}
          />
        </section>
      </main>

      <ReportModal
        open={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        rows={tableData.rows}
        totalArea={tableData.totalArea}
        totalCount={tableData.totalCount}
        countLabel={tableData.countLabel}
        summaryMode={effectiveSummaryMode}
        summaryScope={summaryScopeLabel}
      />
    </div>
  );
}

function createViewStateFromBoundary(boundary) {
  const [minLng, minLat, maxLng, maxLat] = getBoundsFromGeoJson(boundary);
  const longitude = (minLng + maxLng) / 2;
  const latitude = (minLat + maxLat) / 2;
  const lngSpan = Math.max(maxLng - minLng, 0.01);
  const latSpan = Math.max(maxLat - minLat, 0.01);
  const zoom = Math.min(
    14,
    Math.max(10.5, Math.log2(360 / Math.max(lngSpan * 18, latSpan * 28))),
  );

  return {
    longitude: longitude || SONGPA_VIEW_STATE.longitude,
    latitude: latitude || SONGPA_VIEW_STATE.latitude,
    zoom: Math.max(SONGPA_VIEW_STATE.zoom, zoom),
    pitch: 0,
    bearing: 0,
  };
}

export default App;
