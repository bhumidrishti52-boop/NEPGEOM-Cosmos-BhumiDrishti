import ee
import math

ASSET_ID = 'projects/flood-482116/assets/Bhumi_Full_Production_Final'

BAND_MEDIANS = {
    'flood_risk':       0.15,
    'landslide_risk':   0.25,
    'agri_suitability': 0.40,
    'elevation':        180.0,
    'slope':            3.0,
    'slope_std':        1.0,
    'curvature':        0.0,
    'NDVI':             0.408,
    'ndvi_wet':         0.779,
    'ndvi_delta':       0.414,
    'rain':             1760.0,
    'lulc':             40.0,
    'soil_clay':        22.0,
    'twi':              6.5,
    'spi':              -0.80,
    'dist_river_log':   5.0,
    'flow_acc_log':     5.0,
}

LULC_MAP = {
    10: 'Forest',
    20: 'Shrubland',
    30: 'Grassland',
    40: 'Cropland',
    50: 'Built-up',
    60: 'Bare/Sparse Vegetation',
    80: 'Permanent Water',
    95: 'Wetland',
    97: 'Other',
}

def _lulc_label(code: int) -> str:
    return LULC_MAP.get(int(code), f'Unknown ({code})')


def _dist_river_metres(dist_river_log: float) -> int:
    return round(math.exp(dist_river_log) - 1)


def _clay_percent(soil_clay_g_per_kg: float) -> float:
    return soil_clay_g_per_kg / 10.0


def _spi_interpretation(spi: float) -> str:
    if spi >= -0.40:
        return 'HIGH (strong stream power / erosion risk)'
    elif spi >= -0.80:
        return 'MODERATE'
    else:
        return 'LOW'

def _determine_confidence(area_m2: float):
    if area_m2 >= 2700:
        return 'HIGH', 0, 0
    elif area_m2 >= 900:
        return 'MEDIUM', 1, 30
    else:
        return 'LOW', 2, 60

def run_spatial_analysis(geometry_dict: dict) -> dict:
    geom_raw = ee.Geometry(geometry_dict)
    centroid = geom_raw.centroid(maxError=1)
    centroid_coords = centroid.coordinates().getInfo()
    print(f"DEBUG: Centroid (lon, lat): {centroid_coords}")

    area_m2 = geom_raw.area(maxError=1).getInfo()
    print(f"DEBUG: Plot area = {area_m2:.1f} m²")
    confidence, buffer_tier, buffer_m = _determine_confidence(area_m2)

    if buffer_m > 0:
        geom_analysis = geom_raw.buffer(buffer_m, maxError=1)
        print(f"DEBUG: Buffering {buffer_m} m (confidence={confidence})")
    else:
        geom_analysis = geom_raw

    try:
        image = ee.Image(ASSET_ID)
    except Exception as e:
        print(f"ERROR loading asset: {e}")
        return {}

    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.max(), sharedInputs=True)
        .combine(ee.Reducer.min(), sharedInputs=True)
        .combine(ee.Reducer.stdDev(), sharedInputs=True)
    )

    try:
        stats = image.reduceRegion(
            reducer=reducer,
            geometry=geom_analysis,
            scale=30,
            maxPixels=1e8,
            bestEffort=True,
        ).getInfo()
    except Exception as e:
        print(f"GEE reduceRegion error: {e}")
        return {}

    print(f"DEBUG: Raw GEE stats keys: {list(stats.keys())}")