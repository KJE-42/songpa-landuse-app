function createRasterStyle({
  sourceId,
  tiles,
  attribution,
  tileSize = 256,
  maxzoom = 20,
  rasterOpacity = 1,
  brightnessMin = 0,
  brightnessMax = 1,
  saturation = 0,
  contrast = 0,
}) {
  return {
    version: 8,
    sources: {
      [sourceId]: {
        type: 'raster',
        tiles,
        tileSize,
        attribution,
        maxzoom,
      },
    },
    layers: [
      {
        id: `${sourceId}-basemap`,
        type: 'raster',
        source: sourceId,
        minzoom: 0,
        maxzoom: 22,
        paint: {
          'raster-opacity': rasterOpacity,
          'raster-saturation': saturation,
          'raster-contrast': contrast,
          'raster-brightness-min': brightnessMin,
          'raster-brightness-max': brightnessMax,
        },
      },
    ],
  };
}

export const BASEMAPS = {
  general: {
    key: 'general',
    label: '일반 지도',
    style: createRasterStyle({
      sourceId: 'osm-general',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      attribution: '© OpenStreetMap contributors',
      rasterOpacity: 1,
    }),
  },
  light: {
    key: 'light',
    label: '밝은 지도',
    style: createRasterStyle({
      sourceId: 'carto-light',
      tiles: ['https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],
      attribution: '© OpenStreetMap contributors © CARTO',
      rasterOpacity: 0.98,
      brightnessMin: 0.03,
      brightnessMax: 0.99,
      saturation: -0.08,
      contrast: -0.03,
    }),
  },
  none: {
    key: 'none',
    label: '배경 없음',
    style: {
      version: 8,
      sources: {},
      layers: [
        {
          id: 'plain-background',
          type: 'background',
          paint: {
            'background-color': '#e6ecef',
          },
        },
      ],
    },
  },
};

export const DEFAULT_BASEMAP_KEY = 'general';

export const BASEMAP_OPTIONS = Object.values(BASEMAPS).map(({ key, label }) => ({
  key,
  label,
}));

