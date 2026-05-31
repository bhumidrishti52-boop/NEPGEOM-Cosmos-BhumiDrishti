// Mapbox / MapLibre Key
const MAPTILER_KEY = 'VSrXKSaprVudRxsjfdAF';

// Define exact GEE region bounds
const bounds = [
    [86.9816852324489, 26.572226888007714], // Southwest
    [87.34088811330828, 26.849841970232982] // Northeast
];

// Center of the map
const center = [
    (86.9916852324489 + 87.33088811330828) / 2,
    (26.582226888007714 + 26.839841970232982) / 2
];

// Initialize Map
const map = new maplibregl.Map({
    container: 'map',
    style: `https://api.maptiler.com/maps/hybrid/style.json?key=${MAPTILER_KEY}`,
    center: center,
    zoom: 11,
    minZoom: 5,   // allow zoom out
    maxZoom: 20
});

// Expose for debugging/submodules
window.map = map;

// Add navigation controls (zoom in/out, compass)
map.addControl(new maplibregl.NavigationControl(), 'bottom-right');

// Fit map exactly to GEE region on load
map.on('load', () => {
    map.fitBounds(bounds, { padding: 50, linear: true });
});