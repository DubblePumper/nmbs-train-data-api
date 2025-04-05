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

**Response:** De GTFS real-time gegevens als JSON

### GET `/api/planningdata/data`

Haal een overzicht op van alle beschikbare planningsgegevens.

**Response:**
```json
{
  "message": "Planning data available at the following endpoints",
  "files": ["stops.txt", "routes.txt", "calendar.txt", ...],
  "endpoints": {
    "stops": "http://<server-ip>:<port>/api/planningdata/stops",
    "routes": "http://<server-ip>:<port>/api/planningdata/routes",
    ...
  }
}
```

### GET `/api/planningdata/files`

Haal een lijst op van alle beschikbare planningsdatabestanden.

**Response:**
```json
{
  "files": ["stops.txt", "routes.txt", "calendar.txt", ...]
}
```

### GET `/api/planningdata/<filename>`

Haal de inhoud van een specifiek planningsdatabestand op.

**Parameters:**
- `filename`: De naam van het op te halen bestand (met of zonder extensie)

**Response:** De bestandsinhoud als JSON

### GET `/api/planningdata/stops`

Haal de stops.txt gegevens op met stationsinformatie.

**Response:** De stops.txt gegevens als JSON

### GET `/api/planningdata/routes`

Haal de routes.txt gegevens op met route-informatie.

**Response:** De routes.txt gegevens als JSON

### GET `/api/planningdata/calendar`

Haal de calendar.txt gegevens op met dienstregeling kalenderinformatie.

**Response:** De calendar.txt gegevens als JSON

### GET `/api/planningdata/trips`

Haal de trips.txt gegevens op met rit-informatie.

**Response:** De trips.txt gegevens als JSON

### GET `/api/planningdata/stop_times`

Haal de stop_times.txt gegevens op met haltetijdinformatie.

**Parameters:**
| Parameter | Beschrijving | Standaardwaarde |
|-----------|--------------|-----------------|
| `page` | Paginanummer beginnend vanaf 0 | 0 |
| `limit` | Aantal records per pagina | 1000 (max: 5000) |
| `search` | Zoektekst om haltetijden te filteren | - |
| `field` | Specifiek veld om in te zoeken (bijv. 'stop_id') | - |
| `sort_by` | Veld om op te sorteren (bijv. 'arrival_time') | - |
| `sort_direction` | Sorteerrichting (asc of desc) | - |
| `stop_id` | Filter op specifieke stop_id | - |
| `trip_id` | Filter op specifieke trip_id | - |
| `arrival_time` | Filter op specifieke aankomsttijd (formaat: HH:MM:SS) | - |
| `departure_time` | Filter op specifieke vertrektijd (formaat: HH:MM:SS) | - |

**Response:** De stop_times.txt gegevens als JSON met paginering metadata

**Voorbeeld:**
```json
{
  "data": [
    {
      "trip_id": "88____",
      "arrival_time": "05:24:00",
      "departure_time": "05:24:00",
      "stop_id": "8861606",
      "stop_sequence": "0",
      "pickup_type": "0",
      "drop_off_type": "0"
    },
    ...
  ],
  "pagination": {
    "page": 0,
    "pageSize": 1000,
    "totalRecords": 125000,
    "totalPages": 125,
    "hasNextPage": true,
    "hasPrevPage": false
  }
}
```

### GET `/api/planningdata/calendar_dates`

Haal de calendar_dates.txt gegevens op met uitzonderingsdatums.

**Response:** De calendar_dates.txt gegevens als JSON

### GET `/api/planningdata/agency`

Haal de agency.txt gegevens op met vervoerdersinformatie.

**Response:** De agency.txt gegevens als JSON

### GET `/api/planningdata/translations`

Haal de translations.txt gegevens op met vertaalinformatie.

**Response:** De translations.txt gegevens als JSON

### POST `/api/update`

Forceer een onmiddellijke update van alle gegevens.

**Response:**
```json
{
  "status": "success",
  "message": "Data updated successfully"
}
```

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

**Response:** The GTFS real-time data as JSON

### GET `/api/planningdata/data`

Retrieve an overview of all available planning data.

**Response:**
```json
{
  "message": "Planning data available at the following endpoints",
  "files": ["stops.txt", "routes.txt", "calendar.txt", ...],
  "endpoints": {
    "stops": "http://<server-ip>:<port>/api/planningdata/stops",
    "routes": "http://<server-ip>:<port>/api/planningdata/routes",
    ...
  }
}
```

### GET `/api/planningdata/files`

Retrieve a list of all available planning data files.

**Response:**
```json
{
  "files": ["stops.txt", "routes.txt", "calendar.txt", ...]
}
```

### GET `/api/planningdata/<filename>`

Retrieve the content of a specific planning data file.

**Parameters:**
- `filename`: The name of the file to retrieve (with or without extension)

**Response:** The file content as JSON

### GET `/api/planningdata/stops`

Retrieve the stops.txt data with station information.

**Response:** The stops.txt data as JSON

### GET `/api/planningdata/routes`

Retrieve the routes.txt data with route information.

**Response:** The routes.txt data as JSON

### GET `/api/planningdata/calendar`

Retrieve the calendar.txt data with service schedule calendar information.

**Response:** The calendar.txt data as JSON

### GET `/api/planningdata/trips`

Retrieve the trips.txt data with trip information.

**Response:** The trips.txt data as JSON

### GET `/api/planningdata/stop_times`

Retrieve the stop_times.txt data with stop time information.

**Parameters:**
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `page` | Page number starting from 0 | 0 |
| `limit` | Number of records per page | 1000 (max: 5000) |
| `search` | Search text to filter stop times | - |
| `field` | Specific field to search in (e.g., 'stop_id') | - |
| `sort_by` | Field to sort by (e.g., 'arrival_time') | - |
| `sort_direction` | Sort direction (asc or desc) | - |
| `stop_id` | Filter by specific stop_id | - |
| `trip_id` | Filter by specific trip_id | - |
| `arrival_time` | Filter by specific arrival time (format: HH:MM:SS) | - |
| `departure_time` | Filter by specific departure time (format: HH:MM:SS) | - |

**Response:** The stop_times.txt data as JSON with pagination metadata

**Example:**
```json
{
  "data": [
    {
      "trip_id": "88____",
      "arrival_time": "05:24:00",
      "departure_time": "05:24:00",
      "stop_id": "8861606",
      "stop_sequence": "0",
      "pickup_type": "0",
      "drop_off_type": "0"
    },
    ...
  ],
  "pagination": {
    "page": 0,
    "pageSize": 1000,
    "totalRecords": 125000,
    "totalPages": 125,
    "hasNextPage": true,
    "hasPrevPage": false
  }
}
```

### GET `/api/planningdata/calendar_dates`

Retrieve the calendar_dates.txt data with exception dates.

**Response:** The calendar_dates.txt data as JSON

### GET `/api/planningdata/agency`

Retrieve the agency.txt data with carrier information.

**Response:** The agency.txt data as JSON

### GET `/api/planningdata/translations`

Retrieve the translations.txt data with translation information.

**Response:** The translations.txt data as JSON

### POST `/api/update`

Force an immediate update of all data.

**Response:**
```json
{
  "status": "success",
  "message": "Data updated successfully"
}
```

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
