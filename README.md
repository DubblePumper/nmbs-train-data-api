# NMBS Train Data API | Vibe Coding

<div align="center">

![NMBS/SNCB Logo](https://img.shields.io/badge/NMBS%2FSNCB-API-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.0.0-brightgreen?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge)

</div>

*[English version below](#nmbs-train-data-api--vibe-coding-1)*

Een zelfstandige API voor het verkrijgen van real-time en planningsgegevens van de Belgische spoorwegen (NMBS/SNCB).

> 🔗 Deze API maakt deel uit van het hoofdproject: [NMBS-Train-data](https://github.com/DubblePumper/NMBS-Train-data)

## 📋 Inhoudsopgave
- [Kenmerken](#kenmerken)
- [Installatie](#installatie)
- [Configuratie](#configuratie)
- [Gebruik](#gebruik)
  - [Als zelfstandige service](#als-zelfstandige-service)
  - [Als Web API](#als-web-api)
  - [In je applicatie](#in-je-applicatie)
  - [Caching van data](#caching-van-data)
  - [Toegang vanuit Pelican Panel](#toegang-vanuit-pelican-panel)
- [Service-opties](#service-opties)
- [API Referentie](#api-referentie)
- [Web API Endpoints](#web-api-endpoints)
- [Gegevensstructuur](#gegevensstructuur)
- [Licentie](#licentie)
- [Dankbetuigingen](#dankbetuigingen)

## ✨ Kenmerken

- Haalt efficiënt real-time NMBS treingegevens op
- Downloadt en verwerkt GTFS planningsgegevens met perroninformatie
- Verwerkt Cloudflare-beveiliging bij het scrapen van de officiële website
- Slaat gegevens lokaal op voor snelle toegang
- Minimaliseert webscraping-operaties door gegevensverzameling te scheiden van toegang
- Biedt een eenvoudige API voor je toepassingen
- Kan draaien als een zelfstandige service of in je applicatie worden geïntegreerd
- Inclusief een web API voor het benaderen van gegevens via HTTP-verzoeken, perfect voor Pelican panel integratie

## 🚀 Installatie

```bash
# Clone the repository
git clone https://github.com/yourusername/nmbs-train-data-api.git
cd nmbs-train-data-api

# Install the package
pip install -e .
```

## ⚙️ Configuratie

Maak een `.env` bestand aan in de hoofdmap met de volgende inhoud:

```ini
# NMBS API Configuration
NMBS_DATA_URL=URL_GEGEVEN_DOOR_GEBRUIKER

# Cloudflare Bypass Settings
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/117.0.0.0
COOKIES_FILE=data/cookies.json

# Web API Settings
API_PORT=25580
API_HOST=0.0.0.0
```

Je kunt de `API_PORT` waarde eenvoudig aanpassen om te wijzigen op welke poort de web API draait.

## 🔧 Gebruik

### Als zelfstandige service

Je kunt de API als een zelfstandige service draaien die continu de nieuwste gegevens ophaalt:

```bash
# Draaien met standaardinstellingen (elke 30 seconden downloaden, website eenmaal per dag scrapen)
python service.py

# Draaien met aangepaste intervallen
python service.py --interval 30 --scrape-interval 43200 --data-dir my_data_folder
```

### Als Web API

Je kunt de API als webserver draaien die endpoints biedt voor toegang tot de gegevens:

```bash
# De web API draaien met standaardinstellingen (host en poort uit .env bestand)
python run_web_api.py

# Draaien met aangepaste host en poort
python run_web_api.py --host 127.0.0.1 --port 8080 --debug
```

### In je applicatie

```python
from nmbs_api import get_realtime_data, get_planning_file, start_data_service

# Start de service in de achtergrond wanneer je applicatie start
start_data_service()

# Later, haal de nieuwste real-time gegevens op wanneer je ze nodig hebt
realtime_data = get_realtime_data()

# Of haal specifieke planningsgegevens op
stops_data = get_planning_file('stops.txt')

# Verwerk de gegevens...
# De gegevens worden automatisch up-to-date gehouden door de achtergrondservice
```

### Caching van data

Wanneer de API draait, worden automatisch de eerste 25 records van elk endpoint opgeslagen in een JSON-bestand. Dit cachebestand wordt elke 2 minuten bijgewerkt om de gegevens actueel te houden zonder de server te belasten. Deze functie zorgt voor snellere responstijden bij veelgebruikte verzoeken.

### Toegang vanuit Pelican Panel

Je kunt de NMBS Train Data API vanaf je Pelican panel benaderen door HTTP-verzoeken in te stellen naar de volgende endpoints:

| Endpoint | Beschrijving |
|----------|--------------|
| `http://<server-ip>:<port>/api/health` | Controleer of de API draait |
| `http://<server-ip>:<port>/api/realtime/data` | Haal de nieuwste real-time treingegevens op |
| `http://<server-ip>:<port>/api/planningdata/stops` | Haal stationsgegevens op uit planningsdata |
| `http://<server-ip>:<port>/api/update` | Forceer een onmiddellijke update van de gegevens (POST-verzoek) |

Vervang `<server-ip>` door het IP-adres van de computer waarop de API draait en `<port>` door de poort die in je `.env` bestand is opgegeven (standaard: 25580).

## ⚡ Service-opties

De zelfstandige service (`service.py`) accepteert de volgende command-line opties:

| Optie | Beschrijving | Standaardwaarde |
|-------|--------------|-----------------|
| `--interval` | Tijd in seconden tussen gegevensdownloads | 30 |
| `--scrape-interval` | Tijd in seconden tussen webscraping-operaties | 86400 (eenmaal per dag) |
| `--log-file` | Pad naar het logbestand | nmbs_service.log |
| `--data-dir` | Directory om gegevensbestanden op te slaan | data |

## 📚 API Referentie

### `start_data_service()`

Start de NMBS dataservice in de achtergrond. Dit zal:
1. Een initiële scrape van de website doen indien nodig
2. De nieuwste gegevensbestanden downloaden
3. In de achtergrond blijven draaien om de gegevens regelmatig bij te werken

**Returns:** Een achtergrond-thread die de service draait

### `get_realtime_data()`

Haalt de nieuwste real-time NMBS-gegevens op met spoorwijzigingen.

**Returns:** De GTFS real-time gegevens als een dictionary

### `get_planning_files_list()`

Haalt een lijst op van beschikbare planningsdatabestanden.

**Returns:** Een lijst met bestandsnamen

### `get_planning_file(filename)`

Haalt de inhoud van een specifiek planningsdatabestand op.

**Parameters:**
- `filename` (str): Naam van het bestand om op te halen

**Returns:** De bestandsinhoud als JSON (voor CSV/TXT bestanden) of als string (voor andere bestanden)

### `force_update()`

Forceert een onmiddellijke update van de gegevens.

**Returns:** True indien succesvol

## 🌐 Web API Endpoints

### GET `/api/health`

Een eenvoudig health check endpoint dat de status van de API teruggeeft.

**Response:**
```json
{
  "status": "healthy",
  "service": "NMBS Train Data API"
}
```

### GET `/api/realtime/data`

Haal de nieuwste real-time treingegevens op met spoorwijzigingen.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `search` | Veld waarop gezocht moet worden (bijv. 'id', 'stopId', 'timestamp') | - |
| `<search>` | De waarde waarop gefilterd moet worden wanneer 'search' is ingesteld | - |
| `exact` | Of er exact (true) of gedeeltelijk (false) moet worden gezocht | false |
| `limit` | Maximum aantal resultaten om terug te geven | 1000 |

**Voorbeelden:**
```
/api/realtime/data?search=id&id=88____:007::8831310:8884335:48:1050:20251212
/api/realtime/data?search=stopId&stopId=8831310_2
/api/realtime/data?search=timestamp&timestamp=1744361475
```

**Response:** De GTFS real-time gegevens als JSON, gefilterd op zoekparameters

### GET `/api/planningdata/<filename>`

Haal de inhoud van een specifiek planningsdatabestand op.

**Parameters:**
- `filename`: De naam van het op te halen bestand (met of zonder extensie)
- `search`: Veld waarop gezocht moet worden (bijv. 'stop_name', 'route_id', etc.)
- `<search>`: De waarde waarop gefilterd moet worden wanneer 'search' is ingesteld
- `exact`: Of er exact (true) of gedeeltelijk (false) moet worden gezocht
- `limit`: Maximum aantal resultaten om terug te geven (standaard: 1000, max: 5000)

**Voorbeelden:**
```
/api/planningdata/stops?search=stop_name&stop_name=Brussels&exact=false
/api/planningdata/routes?search=route_short_name&route_short_name=IC&exact=true
/api/planningdata/calendar?search=service_id&service_id=1
```

**Response:** De bestandsinhoud als JSON, gefilterd op zoekparameters

### GET `/api/planningdata/stops`

Haal de stops.txt gegevens op met stationsinformatie.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `search` | Veld waarop gezocht moet worden (bijv. 'stop_name', 'stop_id', 'stop_lat', 'stop_lon') | - |
| `stop_name` | Filter op naam van het station | - |
| `stop_id` | Filter op station ID | - |
| `stop_lat` | Filter op breedtegraad | - |
| `stop_lon` | Filter op lengtegraad | - |
| `zone_id` | Filter op zone ID | - |
| `parent_station` | Filter op bovenliggend station | - |
| `platform_code` | Filter op perroncode | - |
| `exact` | Of er exact (true) of gedeeltelijk (false) moet worden gezocht | false |
| `limit` | Aantal records per pagina | 1000 (max: 5000) |
| `page` | Paginanummer beginnend vanaf 0 | 0 |

**Voorbeelden:**
```
/api/planningdata/stops?search=stop_name&stop_name=Brussels
/api/planningdata/stops?search=stop_id&stop_id=8831310
/api/planningdata/stops?search=stop_lat&stop_lat=50.85&exact=false
```

### GET `/api/planningdata/routes`

Haal de routes.txt gegevens op met route-informatie.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `search` | Veld waarop gezocht moet worden (bijv. 'route_id', 'route_short_name', 'route_long_name') | - |
| `route_id` | Filter op route ID | - |
| `route_short_name` | Filter op korte naam | - |
| `route_long_name` | Filter op lange naam | - |
| `route_type` | Filter op routetype | - |
| `agency_id` | Filter op agency ID | - |
| `exact` | Of er exact (true) of gedeeltelijk (false) moet worden gezocht | false |
| `limit` | Aantal records per pagina | 1000 (max: 5000) |
| `page` | Paginanummer beginnend vanaf 0 | 0 |

### GET `/api/planningdata/calendar`

Haal de calendar.txt gegevens op met dienstregeling kalenderinformatie.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `search` | Veld waarop gezocht moet worden (bijv. 'service_id', 'start_date', 'end_date') | - |
| `service_id` | Filter op service ID | - |
| `start_date` | Filter op startdatum | - |
| `end_date` | Filter op einddatum | - |
| `monday` | Filter op maandagservice (0 of 1) | - |
| `tuesday` | Filter op dinsdagservice (0 of 1) | - |
| `wednesday` | Filter op woensdagservice (0 of 1) | - |
| `thursday` | Filter op donderdagservice (0 of 1) | - |
| `friday` | Filter op vrijdagservice (0 of 1) | - |
| `saturday` | Filter op zaterdagservice (0 of 1) | - |
| `sunday` | Filter op zondagservice (0 of 1) | - |
| `exact` | Of er exact (true) of gedeeltelijk (false) moet worden gezocht | false |
| `limit` | Aantal records per pagina | 1000 (max: 5000) |
| `page` | Paginanummer beginnend vanaf 0 | 0 |

### GET `/api/planningdata/trips`

Haal de trips.txt gegevens op met rit-informatie.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `search` | Veld waarop gezocht moet worden (bijv. 'route_id', 'service_id', 'trip_id', 'trip_headsign') | - |
| `route_id` | Filter op route ID | - |
| `service_id` | Filter op service ID | - |
| `trip_id` | Filter op trip ID | - |
| `trip_headsign` | Filter op ritbestemming | - |
| `trip_short_name` | Filter op korte ritnaam | - |
| `direction_id` | Filter op richting ID | - |
| `exact` | Of er exact (true) of gedeeltelijk (false) moet worden gezocht | false |
| `limit` | Aantal records per pagina | 1000 (max: 5000) |
| `page` | Paginanummer beginnend vanaf 0 | 0 |

### GET `/api/planningdata/stop_times`

Haal de stop_times.txt gegevens op met haltetijdinformatie.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `search` | Veld waarop gezocht moet worden (bijv. 'trip_id', 'stop_id', 'arrival_time', 'departure_time') | - |
| `trip_id` | Filter op trip ID | - |
| `stop_id` | Filter op stop ID | - |
| `arrival_time` | Filter op aankomsttijd (formaat: HH:MM:SS) | - |
| `departure_time` | Filter op vertrektijd (formaat: HH:MM:SS) | - |
| `stop_sequence` | Filter op stopvolgorde | - |
| `stop_headsign` | Filter op stopbestemming | - |
| `pickup_type` | Filter op ophaaltype | - |
| `drop_off_type` | Filter op afzettype | - |
| `exact` | Of er exact (true) of gedeeltelijk (false) moet worden gezocht | false |
| `limit` | Aantal records per pagina | 1000 (max: 5000) |
| `page` | Paginanummer beginnend vanaf 0 | 0 |

### GET `/api/planningdata/calendar_dates`

Haal de calendar_dates.txt gegevens op met uitzonderingsdatums.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `search` | Veld waarop gezocht moet worden (bijv. 'service_id', 'date', 'exception_type') | - |
| `service_id` | Filter op service ID | - |
| `date` | Filter op datum | - |
| `exception_type` | Filter op uitzonderingstype | - |
| `exact` | Of er exact (true) of gedeeltelijk (false) moet worden gezocht | false |
| `limit` | Aantal records per pagina | 1000 (max: 5000) |
| `page` | Paginanummer beginnend vanaf 0 | 0 |

**Voorbeeld:**
```
/api/planningdata/calendar_dates?search=date&date=20250408
```

**Response:** De calendar_dates.txt gegevens als JSON, gefilterd op zoekparameters

### GET `/api/planningdata/agency`

Haal de agency.txt gegevens op met vervoerdersinformatie.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `search` | Veld waarop gezocht moet worden (bijv. 'agency_id', 'agency_name') | - |
| `agency_id` | Filter op agency ID | - |
| `agency_name` | Filter op agency naam | - |
| `agency_url` | Filter op agency URL | - |
| `agency_timezone` | Filter op agency tijdzone | - |
| `agency_lang` | Filter op agency taal | - |
| `exact` | Of er exact (true) of gedeeltelijk (false) moet worden gezocht | false |
| `limit` | Aantal records per pagina | 1000 (max: 5000) |
| `page` | Paginanummer beginnend vanaf 0 | 0 |

**Voorbeeld:**
```
/api/planningdata/agency?search=agency_name&agency_name=NMBS
```

**Response:** De agency.txt gegevens als JSON, gefilterd op zoekparameters

### GET `/api/planningdata/translations`

Haal de translations.txt gegevens op met vertaalinformatie.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `search` | Veld waarop gezocht moet worden (bijv. 'table_name', 'field_name', 'language', 'translation') | - |
| `table_name` | Filter op tabelnaam | - |
| `field_name` | Filter op veldnaam | - |
| `language` | Filter op taalcode | - |
| `translation` | Filter op vertaaltekst | - |
| `record_id` | Filter op record ID | - |
| `field_value` | Filter op veldwaarde | - |
| `exact` | Of er exact (true) of gedeeltelijk (false) moet worden gezocht | false |
| `limit` | Aantal records per pagina | 1000 (max: 5000) |
| `page` | Paginanummer beginnend vanaf 0 | 0 |

**Voorbeelden:**
```
/api/planningdata/translations?search=language&language=nl
/api/planningdata/translations?search=translation&translation=Brussel
```

**Response:** De translations.txt gegevens als JSON, gefilterd op zoekparameters

## 📊 Gegevensstructuur

### Real-time gegevens

De API geeft real-time gegevens terug in standaard GTFS Realtime formaat, geconverteerd naar een Python dictionary. De structuur volgt de [GTFS Realtime specificatie](https://developers.google.com/transit/gtfs-realtime).

### Planningsgegevens

Planningsgegevens worden teruggegeven als JSON objecten die zijn geconverteerd van de oorspronkelijke GTFS tekstbestanden. De structuur volgt de [GTFS statische gegevensspecificatie](https://developers.google.com/transit/gtfs/reference).

## 📜 Licentie

Dit project is gelicenseerd onder de MIT-licentie - zie het LICENSE-bestand voor details.

## 👏 Dankbetuigingen

- NMBS/SNCB voor het verstrekken van de openbare treingegevens
- De GTFS Realtime en GTFS specificaties

---

# NMBS Train Data API | Vibe Coding

<div align="center">

![NMBS/SNCB Logo](https://img.shields.io/badge/NMBS%2FSNCB-API-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.0.0-brightgreen?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge)

</div>

A standalone API for retrieving real-time and scheduling data from the Belgian railways (NMBS/SNCB).

> 🔗 This API is part of the main project: [NMBS-Train-data](https://github.com/DubblePumper/NMBS-Train-data)

## 📋 Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [As a Standalone Service](#as-a-standalone-service)
  - [As a Web API](#as-a-web-api)
  - [In Your Application](#in-your-application)
  - [Caching Data](#caching-data)
  - [Access from Pelican Panel](#access-from-pelican-panel)
- [Service Options](#service-options)
- [API Reference](#api-reference)
- [Web API Endpoints](#web-api-endpoints-1)
- [Data Structure](#data-structure)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## ✨ Features

- Efficiently retrieves real-time NMBS train data
- Downloads and processes GTFS scheduling data with platform information
- Handles Cloudflare security when scraping the official website
- Stores data locally for fast access
- Minimizes web scraping operations by separating data collection from access
- Provides a simple API for your applications
- Can run as a standalone service or be integrated into your application
- Includes a web API for accessing data via HTTP requests, perfect for Pelican panel integration

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/nmbs-train-data-api.git
cd nmbs-train-data-api

# Install the package
pip install -e .
```

## ⚙️ Configuration

Create a `.env` file in the root directory with the following content:

```ini
# NMBS API Configuration
NMBS_DATA_URL=URL_PROVIDED_BY_USER

# Cloudflare Bypass Settings
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/117.0.0.0
COOKIES_FILE=data/cookies.json

# Web API Settings
API_PORT=25580
API_HOST=0.0.0.0
```

You can easily adjust the `API_PORT` value to change which port the web API runs on.

## 🔧 Usage

### As a Standalone Service

You can run the API as a standalone service that continuously fetches the latest data:

```bash
# Run with default settings (download every 30 seconds, scrape website once a day)
python service.py

# Run with custom intervals
python service.py --interval 30 --scrape-interval 43200 --data-dir my_data_folder
```

### As a Web API

You can run the API as a web server that provides endpoints for accessing the data:

```bash
# Run the web API with default settings (host and port from .env file)
python run_web_api.py

# Run with custom host and port
python run_web_api.py --host 127.0.0.1 --port 8080 --debug
```

### In Your Application

```python
from nmbs_api import get_realtime_data, get_planning_file, start_data_service

# Start the service in the background when your application starts
start_data_service()

# Later, retrieve the latest real-time data when you need it
realtime_data = get_realtime_data()

# Or retrieve specific planning data
stops_data = get_planning_file('stops.txt')

# Process the data...
# The data is automatically kept up-to-date by the background service
```

### Caching Data

When the API is running, the first 25 records of each endpoint are automatically stored in a JSON file. This cache file is updated every 2 minutes to keep the data current without overloading the server. This feature ensures faster response times for frequently used requests.

### Access from Pelican Panel

You can access the NMBS Train Data API from your Pelican panel by setting up HTTP requests to the following endpoints:

| Endpoint | Description |
|----------|-------------|
| `http://<server-ip>:<port>/api/health` | Check if the API is running |
| `http://<server-ip>:<port>/api/realtime/data` | Retrieve the latest real-time train data |
| `http://<server-ip>:<port>/api/planningdata/stops` | Retrieve station data from planning data |
| `http://<server-ip>:<port>/api/update` | Force an immediate update of the data (POST request) |

Replace `<server-ip>` with the IP address of the computer running the API and `<port>` with the port specified in your `.env` file (default: 25580).

## ⚡ Service Options

The standalone service (`service.py`) accepts the following command-line options:

| Option | Description | Default Value |
|--------|-------------|---------------|
| `--interval` | Time in seconds between data downloads | 30 |
| `--scrape-interval` | Time in seconds between web scraping operations | 86400 (once per day) |
| `--log-file` | Path to the log file | nmbs_service.log |
| `--data-dir` | Directory to store data files | data |

## 📚 API Reference

### `start_data_service()`

Starts the NMBS data service in the background. This will:
1. Do an initial scrape of the website if needed
2. Download the latest data files
3. Continue running in the background to update the data regularly

**Returns:** A background thread running the service

### `get_realtime_data()`

Retrieves the latest real-time NMBS data with track changes.

**Returns:** The GTFS real-time data as a dictionary

### `get_planning_files_list()`

Retrieves a list of available planning data files.

**Returns:** A list of file names

### `get_planning_file(filename)`

Retrieves the content of a specific planning data file.

**Parameters:**
- `filename` (str): Name of the file to retrieve

**Returns:** The file content as JSON (for CSV/TXT files) or as a string (for other files)

### `force_update()`

Forces an immediate update of the data.

**Returns:** True if successful

## 🌐 Web API Endpoints

### GET `/api/health`

A simple health check endpoint that returns the status of the API.

**Response:**
```json
{
  "status": "healthy",
  "service": "NMBS Train Data API"
}
```

### GET `/api/realtime/data`

Retrieve the latest real-time train data with track changes.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `search` | Field to search in (e.g., 'id', 'stopId', 'timestamp') | - |
| `<search>` | The value to filter by when 'search' is set | - |
| `exact` | Whether to perform exact matching (true) or partial matching (false) | false |
| `limit` | Maximum number of results to return | 1000 |

**Examples:**
```
/api/realtime/data?search=id&id=88____:007::8831310:8884335:48:1050:20251212
/api/realtime/data?search=stopId&stopId=8831310_2
/api/realtime/data?search=timestamp&timestamp=1744361475
```

**Response:** The GTFS real-time data as JSON, filtered by search parameters

### GET `/api/planningdata/<filename>`

Retrieve the content of a specific planning data file.

**Parameters:**
- `filename`: The name of the file to retrieve (with or without extension)
- `search`: Field to search in (e.g., 'stop_name', 'route_id', etc.)
- `<search>`: The value to filter by when 'search' is set
- `exact`: Whether to perform exact matching (true) or partial matching (false)
- `limit`: Maximum number of results to return (default: 1000, max: 5000)

**Examples:**
```
/api/planningdata/stops?search=stop_name&stop_name=Brussels&exact=false
/api/planningdata/routes?search=route_short_name&route_short_name=IC&exact=true
/api/planningdata/calendar?search=service_id&service_id=1
```

**Response:** The file content as JSON, filtered by search parameters

### GET `/api/planningdata/stops`

Retrieve the stops.txt data with station information.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `search` | Field to search in (e.g., 'stop_name', 'stop_id', 'stop_lat', 'stop_lon') | - |
| `stop_name` | Filter by station name | - |
| `stop_id` | Filter by station ID | - |
| `stop_lat` | Filter by latitude | - |
| `stop_lon` | Filter by longitude | - |
| `zone_id` | Filter by zone ID | - |
| `parent_station` | Filter by parent station | - |
| `platform_code` | Filter by platform code | - |
| `exact` | Whether to perform exact matching (true) or partial matching (false) | false |
| `limit` | Number of records per page | 1000 (max: 5000) |
| `page` | Page number starting from 0 | 0 |

**Examples:**
```
/api/planningdata/stops?search=stop_name&stop_name=Brussels
/api/planningdata/stops?search=stop_id&stop_id=8831310
/api/planningdata/stops?search=stop_lat&stop_lat=50.85&exact=false
```

### GET `/api/planningdata/routes`

Retrieve the routes.txt data with route information.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `search` | Field to search in (e.g., 'route_id', 'route_short_name', 'route_long_name') | - |
| `route_id` | Filter by route ID | - |
| `route_short_name` | Filter by short name | - |
| `route_long_name` | Filter by long name | - |
| `route_type` | Filter by route type | - |
| `agency_id` | Filter by agency ID | - |
| `exact` | Whether to perform exact matching (true) or partial matching (false) | false |
| `limit` | Number of records per page | 1000 (max: 5000) |
| `page` | Page number starting from 0 | 0 |

### GET `/api/planningdata/calendar`

Retrieve the calendar.txt data with service schedule calendar information.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `search` | Field to search in (e.g., 'service_id', 'start_date', 'end_date') | - |
| `service_id` | Filter by service ID | - |
| `start_date` | Filter by start date | - |
| `end_date` | Filter by end date | - |
| `monday` | Filter by Monday service (0 or 1) | - |
| `tuesday` | Filter by Tuesday service (0 or 1) | - |
| `wednesday` | Filter by Wednesday service (0 or 1) | - |
| `thursday` | Filter by Thursday service (0 or 1) | - |
| `friday` | Filter by Friday service (0 or 1) | - |
| `saturday` | Filter by Saturday service (0 or 1) | - |
| `sunday` | Filter by Sunday service (0 or 1) | - |
| `exact` | Whether to perform exact matching (true) or partial matching (false) | false |
| `limit` | Number of records per page | 1000 (max: 5000) |
| `page` | Page number starting from 0 | 0 |

### GET `/api/planningdata/trips`

Retrieve the trips.txt data with trip information.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `search` | Field to search in (e.g., 'route_id', 'service_id', 'trip_id', 'trip_headsign') | - |
| `route_id` | Filter by route ID | - |
| `service_id` | Filter by service ID | - |
| `trip_id` | Filter by trip ID | - |
| `trip_headsign` | Filter by trip headsign | - |
| `trip_short_name` | Filter by trip short name | - |
| `direction_id` | Filter by direction ID | - |
| `exact` | Whether to perform exact matching (true) or partial matching (false) | false |
| `limit` | Number of records per page | 1000 (max: 5000) |
| `page` | Page number starting from 0 | 0 |

### GET `/api/planningdata/stop_times`

Retrieve the stop_times.txt data with stop time information.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `search` | Field to search in (e.g., 'trip_id', 'stop_id', 'arrival_time', 'departure_time') | - |
| `trip_id` | Filter by trip ID | - |
| `stop_id` | Filter by stop ID | - |
| `arrival_time` | Filter by arrival time (format: HH:MM:SS) | - |
| `departure_time` | Filter by departure time (format: HH:MM:SS) | - |
| `stop_sequence` | Filter by stop sequence | - |
| `stop_headsign` | Filter by stop headsign | - |
| `pickup_type` | Filter by pickup type | - |
| `drop_off_type` | Filter by drop-off type | - |
| `exact` | Whether to perform exact matching (true) or partial matching (false) | false |
| `limit` | Number of records per page | 1000 (max: 5000) |
| `page` | Page number starting from 0 | 0 |

### GET `/api/planningdata/calendar_dates`

Retrieve the calendar_dates.txt data with exception dates.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `search` | Field to search in (e.g., 'service_id', 'date', 'exception_type') | - |
| `service_id` | Filter by service ID | - |
| `date` | Filter by date | - |
| `exception_type` | Filter by exception type | - |
| `exact` | Whether to perform exact matching (true) or partial matching (false) | false |
| `limit` | Number of records per page | 1000 (max: 5000) |
| `page` | Page number starting from 0 | 0 |

**Example:**
```
/api/planningdata/calendar_dates?search=date&date=20250408
```

**Response:** The calendar_dates.txt data as JSON, filtered by search parameters

### GET `/api/planningdata/agency`

Retrieve the agency.txt data with carrier information.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `search` | Field to search in (e.g., 'agency_id', 'agency_name') | - |
| `agency_id` | Filter by agency ID | - |
| `agency_name` | Filter by agency name | - |
| `agency_url` | Filter by agency URL | - |
| `agency_timezone` | Filter by agency timezone | - |
| `agency_lang` | Filter by agency language | - |
| `exact` | Whether to perform exact matching (true) or partial matching (false) | false |
| `limit` | Number of records per page | 1000 (max: 5000) |
| `page` | Page number starting from 0 | 0 |

**Example:**
```
/api/planningdata/agency?search=agency_name&agency_name=NMBS
```

**Response:** The agency.txt data as JSON, filtered by search parameters

### GET `/api/planningdata/translations`

Retrieve the translations.txt data with translation information.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `search` | Field to search in (e.g., 'table_name', 'field_name', 'language', 'translation') | - |
| `table_name` | Filter by table name | - |
| `field_name` | Filter by field name | - |
| `language` | Filter by language code | - |
| `translation` | Filter by translation text | - |
| `record_id` | Filter by record ID | - |
| `field_value` | Filter by field value | - |
| `exact` | Whether to perform exact matching (true) or partial matching (false) | false |
| `limit` | Number of records per page | 1000 (max: 5000) |
| `page` | Page number starting from 0 | 0 |

**Examples:**
```
/api/planningdata/translations?search=language&language=nl
/api/planningdata/translations?search=translation&translation=Brussel
```

**Response:** The translations.txt data as JSON, filtered by search parameters

## 📊 Data Structure

### Real-time Data

The API returns real-time data in standard GTFS Realtime format, converted to a Python dictionary. The structure follows the [GTFS Realtime specification](https://developers.google.com/transit/gtfs-realtime).

### Planning Data

Planning data is returned as JSON objects converted from the original GTFS text files. The structure follows the [GTFS static data specification](https://developers.google.com/transit/gtfs/reference).

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👏 Acknowledgements

- NMBS/SNCB for providing the public train data
- The GTFS Realtime and GTFS specifications
