# NMBS Train Data API | Vibe Coding

Een zelfstandige API voor het verkrijgen van real-time en planningsgegevens van de Belgische spoorwegen (NMBS/SNCB).

## Kenmerken

- Haalt efficiënt real-time NMBS treingegevens op
- Downloadt en verwerkt GTFS planningsgegevens met perroninformatie
- Verwerkt Cloudflare-beveiliging bij het scrapen van de officiële website
- Slaat gegevens lokaal op voor snelle toegang
- Minimaliseert webscraping-operaties door gegevensverzameling te scheiden van toegang
- Biedt een eenvoudige API voor je toepassingen
- Kan draaien als een zelfstandige service of in je applicatie worden geïntegreerd
- Inclusief een web API voor het benaderen van gegevens via HTTP-verzoeken, perfect voor Pelican panel integratie

## Installatie

```bash
# Clone the repository
git clone https://github.com/yourusername/nmbs-train-data-api.git
cd nmbs-train-data-api

# Install the package
pip install -e .
```

## Configuratie

Maak een `.env` bestand aan in de hoofdmap met de volgende inhoud:

```
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

## Gebruik

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

- `http://<server-ip>:<port>/api/health` - Controleer of de API draait
- `http://<server-ip>:<port>/api/realtime/data` - Haal de nieuwste real-time treingegevens op
- `http://<server-ip>:<port>/api/planningdata/stops` - Haal stationsgegevens op uit planningsdata
- `http://<server-ip>:<port>/api/update` - Forceer een onmiddellijke update van de gegevens (POST-verzoek)

Vervang `<server-ip>` door het IP-adres van de computer waarop de API draait en `<port>` door de poort die in je `.env` bestand is opgegeven (standaard: 25580).

## Service-opties

De zelfstandige service (`service.py`) accepteert de volgende command-line opties:

- `--interval`: Tijd in seconden tussen gegevensdownloads (standaard: 30)
- `--scrape-interval`: Tijd in seconden tussen webscraping-operaties (standaard: 86400, eenmaal per dag)
- `--log-file`: Pad naar het logbestand (standaard: nmbs_service.log)
- `--data-dir`: Directory om gegevensbestanden op te slaan (standaard: data)

## API Referentie

### `start_data_service()`

Start de NMBS dataservice in de achtergrond. Dit zal:
1. Een initiële scrape van de website doen indien nodig
2. De nieuwste gegevensbestanden downloaden
3. In de achtergrond blijven draaien om de gegevens regelmatig bij te werken

Returns: Een achtergrond-thread die de service draait

### `get_realtime_data()`

Haalt de nieuwste real-time NMBS-gegevens op met spoorwijzigingen.

Returns: De GTFS real-time gegevens als een dictionary

### `get_planning_files_list()`

Haalt een lijst op van beschikbare planningsdatabestanden.

Returns: Een lijst met bestandsnamen

### `get_planning_file(filename)`

Haalt de inhoud van een specifiek planningsdatabestand op.

Parameters:
- `filename` (str): Naam van het bestand om op te halen

Returns: De bestandsinhoud als JSON (voor CSV/TXT bestanden) of als string (voor andere bestanden)

### `force_update()`

Forceert een onmiddellijke update van de gegevens.

Returns: True indien succesvol

## Web API Endpoints

### GET `/api/health`

Een eenvoudig health check endpoint dat de status van de API teruggeeft.

Response:
```json
{
  "status": "healthy",
  "service": "NMBS Train Data API"
}
```

### GET `/api/realtime/data`

Haal de nieuwste real-time treingegevens op met spoorwijzigingen.

Response: De GTFS real-time gegevens als JSON

### GET `/api/planningdata/data`

Haal een overzicht op van alle beschikbare planningsgegevens.

Response:
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

Response:
```json
{
  "files": ["stops.txt", "routes.txt", "calendar.txt", ...]
}
```

### GET `/api/planningdata/<filename>`

Haal de inhoud van een specifiek planningsdatabestand op.

Parameters:
- `filename`: De naam van het op te halen bestand (met of zonder extensie)

Response: De bestandsinhoud als JSON

### GET `/api/planningdata/stops`

Haal de stops.txt gegevens op met stationsinformatie.

Response: De stops.txt gegevens als JSON

### GET `/api/planningdata/routes`

Haal de routes.txt gegevens op met route-informatie.

Response: De routes.txt gegevens als JSON

### GET `/api/planningdata/calendar`

Haal de calendar.txt gegevens op met dienstregeling kalenderinformatie.

Response: De calendar.txt gegevens als JSON

### GET `/api/planningdata/trips`

Haal de trips.txt gegevens op met rit-informatie.

Response: De trips.txt gegevens als JSON

### GET `/api/planningdata/stop_times`

Haal de stop_times.txt gegevens op met haltetijdinformatie.

Parameters:
- `page` (int): Paginanummer beginnend vanaf 0 (standaard: 0)
- `limit` (int): Aantal records per pagina (standaard: 1000, max: 5000)
- `search` (str): Zoektekst om haltetijden te filteren
- `field` (str): Specifiek veld om in te zoeken (bijv. 'stop_id')
- `sort_by` (str): Veld om op te sorteren (bijv. 'arrival_time')
- `sort_direction` (str): Sorteerrichting (asc of desc)
- `stop_id` (str): Filter op specifieke stop_id
- `trip_id` (str): Filter op specifieke trip_id
- `arrival_time` (str): Filter op specifieke aankomsttijd (formaat: HH:MM:SS)
- `departure_time` (str): Filter op specifieke vertrektijd (formaat: HH:MM:SS)

Response: De stop_times.txt gegevens als JSON met paginering metadata

Voorbeeld:
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

Response: De calendar_dates.txt gegevens als JSON

### GET `/api/planningdata/agency`

Haal de agency.txt gegevens op met vervoerdersinformatie.

Response: De agency.txt gegevens als JSON

### GET `/api/planningdata/translations`

Haal de translations.txt gegevens op met vertaalinformatie.

Response: De translations.txt gegevens als JSON

### POST `/api/update`

Forceer een onmiddellijke update van alle gegevens.

Response:
```json
{
  "status": "success",
  "message": "Data updated successfully"
}
```

## Gegevensstructuur

### Real-time gegevens

De API geeft real-time gegevens terug in standaard GTFS Realtime formaat, geconverteerd naar een Python dictionary. De structuur volgt de [GTFS Realtime specificatie](https://developers.google.com/transit/gtfs-realtime).

### Planningsgegevens

Planningsgegevens worden teruggegeven als JSON objecten die zijn geconverteerd van de oorspronkelijke GTFS tekstbestanden. De structuur volgt de [GTFS statische gegevensspecificatie](https://developers.google.com/transit/gtfs/reference).

## Licentie

Dit project is gelicenseerd onder de MIT-licentie - zie het LICENSE-bestand voor details.

## Dankbetuigingen

- NMBS/SNCB voor het verstrekken van de openbare treingegevens
- De GTFS Realtime en GTFS specificaties
