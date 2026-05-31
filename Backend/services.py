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