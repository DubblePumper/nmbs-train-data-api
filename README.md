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

## API 

Zie de [API-documentatie](https://github.com/DubblePumper/NMBS-Train-data) voor gedetailleerde informatie over de beschikbare endpoints en hun gebruik.

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
