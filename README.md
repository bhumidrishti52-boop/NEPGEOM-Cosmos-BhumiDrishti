# Bhumi Drishti

Satellite-powered multi-hazard land risk assessment tool for Sunsari District, Nepal.

## Description

Bhumi Drishti is a web platform that delivers instant flood risk, landslide risk, and agricultural suitability scores for any land plot in Sunsari District, Nepal. Built natively on Google Earth Engine using `ee.Classifier.smileRandomForest`, it fuses 13 predictor variables — SRTM elevation, Sentinel-2 imagery, CHIRPS rainfall, and SoilGrids soil data — at 30 m resolution across 1,257 km², with outputs calibrated to Nepal's NDRRMA national risk framework via Platt scaling and spatial 4-block cross-validation. Users draw a plot boundary on an interactive map and receive risk scores, terrain metrics, and AI-generated plain-language explanations within seconds. The platform addresses a critical gap: land buyers in Nepal transact in crore-rupee plots with zero environmental risk data, and farmers lack plot-level drainage and suitability guidance — hazards only discovered after the monsoon hits.

## Getting Started

### Dependencies

* macOS 11+, Ubuntu 20.04+, or Windows 10/11
* Python 3.10 or higher (3.9.6 works but shows deprecation warnings)
* Google Earth Engine account with access to the `Bhumi_Full_Production_Final` asset
* OpenAI API key (`sk-...`) or OpenRouter API key (`sk-or-v1-...`)
* Modern web browser — Chrome, Firefox, Safari, or Edge
* Stable internet connection (required for GEE inference, LLM calls, and map tiles)

### Installing

* Clone the repository from GitHub

```
git clone https://github.com/NEPGEOM-Cosmos-BhumiDrishti/NEPGEOM-Cosmos-BhumiDrishti.git
cd NEPGEOM-Cosmos-BhumiDrishti/Backend
```

* Create and activate a Python virtual environment

```
python3 -m venv .venv
source .venv/bin/activate
```

* Install all required Python packages

```
pip install --upgrade pip
pip install -r requirements.txt
```

* Create a `.env` file inside the `Backend/` folder with the following content

```
OPENAI_API_KEY=sk-or-v1-your-key-here
GEE_PROJECT_ID=your-earth-engine-project-id
BACKEND_PORT=8081
BACKEND_HOST=0.0.0.0
```

* Authenticate with Google Earth Engine (first time only — follow the browser OAuth prompt)

```
python3 -c "import ee; ee.Authenticate(); ee.Initialize(project='your-project-id')"
```

### Executing program

* Start the backend server from the `Backend/` directory

```
python3 main.py
```

* Open a second terminal and serve the frontend from the `Frontend/` directory

```
cd Frontend
python3 -m http.server 8080
```

* Open the app in your browser

```
http://localhost:8080
```

* Click **📍 Draw Plot Boundaries**, click points on the map to outline the land parcel, then double-click to finish — analysis runs automatically and results appear in the sidebar within 3–5 seconds

## Help

Common issues and how to resolve them.

```
python3 -c "import ee; ee.Authenticate()"
```

* Run the above if GEE throws "Earth Engine not initialized" on startup
* If port 8081 is already in use, run `lsof -ti:8081 | xargs kill -9` then restart
* Python 3.9 FutureWarnings from google-auth are warnings only — the app still runs; upgrade to 3.10+ to remove them
* If the map does not load, open DevTools (F12) → Console and confirm both servers are running on ports 8080 and 8081
* `/generate-report` currently returns a 500 error — this endpoint is under development; analyze and chat features work normally

## Acknowledgments

* [Google Earth Engine](https://earthengine.google.com/) — server-side RF training and inference across all 13 predictor variables
* [SRTM](https://www2.jpl.nasa.gov/srtm/) — 30 m elevation, slope, curvature, TWI, SPI
* [Sentinel-2 Copernicus](https://sentinel.esa.int/web/sentinel/missions/sentinel-2) — multispectral imagery for NDVI and land cover
* [CHIRPS](https://www.chc.ucsb.edu/data/chirps) — high-resolution rainfall climatology
* [SoilGrids ISRIC](https://soilgrids.org/) — global soil clay content
* [ESA WorldCover](https://esa-worldcover.org/) — 10 m land use / land cover classification
* [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/) — open-source interactive map rendering
* [LangChain](https://python.langchain.com/) — LLM orchestration for AI risk narratives