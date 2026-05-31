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

    try:
        lulc_mode_result = image.select('lulc').reduceRegion(
            reducer=ee.Reducer.mode(),
            geometry=geom_analysis,
            scale=30,
            maxPixels=1e8,
            bestEffort=True,
        ).getInfo()
        lulc_code = int(lulc_mode_result.get('lulc') or BAND_MEDIANS['lulc'])
    except Exception:
        lulc_code = int(BAND_MEDIANS['lulc'])

    _null_imputed_set: set = set()

    def get_val(band: str, stat: str) -> float:
        key = f"{band}_{stat}"
        v = stats.get(key)
        if v is None:
            _null_imputed_set.add(band)  
            return BAND_MEDIANS.get(band, 0.0)
        return float(v)

    flood_mean   = get_val('flood_risk', 'mean')
    flood_max    = get_val('flood_risk', 'max')

    ls_mean      = get_val('landslide_risk', 'mean')
    ls_max       = get_val('landslide_risk', 'max')

    agri_mean    = get_val('agri_suitability', 'mean')
    agri_max     = get_val('agri_suitability', 'max')

    elev_mean    = get_val('elevation', 'mean')
    elev_min     = get_val('elevation', 'min')
    elev_max     = get_val('elevation', 'max')

    slope_mean   = get_val('slope', 'mean')
    slope_max    = get_val('slope', 'max')

    slope_std    = get_val('slope_std', 'mean')
    curvature    = get_val('curvature', 'mean')

    ndvi_raw     = get_val('NDVI', 'mean')
    ndvi_wet     = get_val('ndvi_wet', 'mean')
    ndvi_delta   = get_val('ndvi_delta', 'mean')

    rain_mean    = get_val('rain', 'mean')

    soil_clay_raw = get_val('soil_clay', 'mean')          
    soil_clay_pct = _clay_percent(soil_clay_raw)       

    twi_mean     = get_val('twi', 'mean')
    spi_mean     = get_val('spi', 'mean')

    dist_river_log = get_val('dist_river_log', 'mean')
    dist_river_m   = _dist_river_metres(dist_river_log)

    flow_acc_log = get_val('flow_acc_log', 'mean')

    outside_roi = not (75 <= elev_mean <= 1267)

    anomaly_flag = (
        flood_mean == 0.0
        and ls_mean < 0.04
        and agri_mean == 0.0
    )

    output = {
        # ─── Asset provenance ────────────────────────────────────
        'source': ASSET_ID,
        'asset_version': 'Bhumi_Full_Production_Final',

        # ─── Confidence / buffer metadata ────────────────────────
        'confidence':   confidence,
        'buffer_tier':  buffer_tier,
        'buffer_m':     buffer_m,
        'area_m2':      round(area_m2, 1),
        'null_imputed': sorted(_null_imputed_set),
        'outside_roi':  outside_roi,
        'anomaly_flag': anomaly_flag,

        # ─── Risk scores (raw 0-1 probabilities) ─────────────────
        'flood_prob': {
            'mean': flood_mean,
            'max':  flood_max,
        },
        'landslide_risk': {
            'mean': ls_mean,
            'max':  ls_max,
        },
        'agri_prob': {
            'mean': agri_mean,
            'max':  agri_max,
        },

        # ─── Terrain ─────────────────────────────────────────────
        'slope': {
            'mean': slope_mean,
            'max':  slope_max,
        },
        'elevation': {
            'mean': elev_mean,
            'min':  elev_min,
            'max':  elev_max,
        },
        'slope_std':  slope_std,
        'curvature':  curvature,

        # ─── Hydrology ───────────────────────────────────────────
        'twi': {
            'mean': twi_mean,
        },
        'spi': {
            'mean':           spi_mean,
            'interpretation': _spi_interpretation(spi_mean),
        },
        'dist_river': {
            'log_value':      dist_river_log,
            'metres':         dist_river_m,
        },
        'flow_acc_log': flow_acc_log,

        # ─── Vegetation ──────────────────────────────────────────
        # NDVI raw is suppressed from user output per contract rule 6
        'vegetation': {
            'ndvi_raw':          ndvi_raw,   # internal only — do NOT expose to users
            'ndvi_wet':          ndvi_wet,
            'ndvi_delta':        ndvi_delta,
            'ndvi_non_informative': True,    # flag for ai_summary / pdf
        },

        # ─── Climate ─────────────────────────────────────────────
        'rainfall': {
            'annual_mm': rain_mean,
        },

        # ─── Soil ─────────────────────────────────────────────────
        'soil_clay': {
            'raw_g_per_kg': soil_clay_raw,
            'percentage':   round(soil_clay_pct, 2),
        },

        # ─── Land use ────────────────────────────────────────────
        'lulc': {
            'code':  lulc_code,
            'label': _lulc_label(lulc_code),
        },
    }

    print(f"DEBUG: confidence={confidence}, buffer_tier={buffer_tier}, "
          f"flood={flood_mean:.3f}, ls={ls_mean:.3f}, agri={agri_mean:.3f}, "
          f"anomaly={anomaly_flag}, outside_roi={outside_roi}")
    return output