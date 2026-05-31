// Initialize MapboxDraw with custom styles
const draw = new MapboxDraw({
    displayControlsDefault: false,
    styles: [
        {
            'id': 'gl-draw-polygon-fill',
            'type': 'fill',
            'filter': ['all', ['==', '$type', 'Polygon']],
            'paint': {
                'fill-color': '#facc15',
                'fill-opacity': 0.4
            }
        },
        {
            'id': 'gl-draw-polygon-stroke',
            'type': 'line',
            'filter': ['all', ['==', '$type', 'Polygon']],
            'paint': {
                'line-color': '#2563eb',
                'line-width': 3,
                'line-dasharray': [2, 1]
            }
        },
        {
            'id': 'gl-draw-point',
            'type': 'circle',
            'filter': ['all', ['==', '$type', 'Point']],
            'paint': {
                'circle-radius': 8,
                'circle-color': '#2563eb',
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff'
            }
        },
        {
            'id': 'gl-draw-point-active',
            'type': 'circle',
            'filter': ['all', ['==', '$type', 'Point'], ['==', 'active', 'true']],
            'paint': {
                'circle-radius': 10,
                'circle-color': '#f97316'
            }
        }
    ]
});

// Expose to window and add to map
window.draw = draw;
map.addControl(draw);
// Logic for user interactions
function startDraw() {
    draw.deleteAll();
    draw.changeMode('draw_polygon');
}

function clearMap() {
    draw.deleteAll();
    
    // Reset UI if it exists in another module
    if (window.resetUI) {
        window.resetUI();
    }

    // Remove GPS marker if exists
    if (window.userMarker) {
        window.userMarker.remove();
    }
}
