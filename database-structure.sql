-- Create a SQLite database for NMBS Train Data
-- This can be adapted for MySQL, PostgreSQL, or other SQL databases

-- PRAGMA foreign_keys = ON;  -- Enable foreign key support (SQLite specific, uncomment if using SQLite)

-- ------------------------------------------------
-- Table structure for GTFS static data
-- ------------------------------------------------

-- Agency information
CREATE TABLE agency (
    agency_id varchar(191) PRIMARY KEY,
    agency_name varchar(255) NOT NULL,
    agency_url varchar(255) NOT NULL,
    agency_timezone varchar(255) NOT NULL,
    agency_lang varchar(255),
    agency_phone varchar(255),
    agency_fare_url varchar(255)
);

-- Stops (stations and platforms)
CREATE TABLE stops (
    stop_id varchar(191) PRIMARY KEY,
    stop_code varchar(255),
    stop_name varchar(255) NOT NULL,
    stop_desc varchar(255),
    stop_lat REAL,
    stop_lon REAL,
    zone_id varchar(255),
    stop_url varchar(255),
    location_type INTEGER,
    parent_station varchar(255),
    platform_code varchar(255),
    wheelchair_boarding INTEGER,
    stop_timezone varchar(255),
    FOREIGN KEY (parent_station) REFERENCES stops(stop_id)
);

-- Create an index for searching stop names efficiently
CREATE INDEX idx_stops_name ON stops(stop_name);

-- Routes information
CREATE TABLE routes (
    route_id varchar(191) PRIMARY KEY,
    agency_id varchar(255),
    route_short_name varchar(255),
    route_long_name varchar(255),
    route_desc varchar(255),
    route_type INTEGER NOT NULL,
    route_url varchar(255),
    route_color varchar(255),
    route_text_color varchar(255),
    FOREIGN KEY (agency_id) REFERENCES agency(agency_id)
);

-- Create indexes for searching routes
CREATE INDEX idx_routes_short_name ON routes(route_short_name);
CREATE INDEX idx_routes_long_name ON routes(route_long_name);

-- Calendar service data (regular service patterns)
CREATE TABLE calendar (
    service_id varchar(191) PRIMARY KEY,
    monday INTEGER NOT NULL,
    tuesday INTEGER NOT NULL,
    wednesday INTEGER NOT NULL,
    thursday INTEGER NOT NULL,
    friday INTEGER NOT NULL,
    saturday INTEGER NOT NULL,
    sunday INTEGER NOT NULL,
    start_date varchar(255) NOT NULL,
    end_date varchar(255) NOT NULL
);

-- Calendar exceptions (holiday schedules, special service days)
CREATE TABLE calendar_dates (
    service_id varchar(191) NOT NULL,
    date varchar(255) NOT NULL,
    exception_type INTEGER NOT NULL,
    PRIMARY KEY (service_id, date),
    FOREIGN KEY (service_id) REFERENCES calendar(service_id)
);

-- Trips (individual train journeys)
CREATE TABLE trips (
    trip_id varchar(191) PRIMARY KEY,
    route_id varchar(255) NOT NULL,
    service_id varchar(255) NOT NULL,
    trip_headsign varchar(255),
    trip_short_name varchar(255),
    direction_id INTEGER,
    block_id varchar(255),
    shape_id varchar(255),
    wheelchair_accessible INTEGER,
    bikes_allowed INTEGER,
    FOREIGN KEY (route_id) REFERENCES routes(route_id),
    FOREIGN KEY (service_id) REFERENCES calendar(service_id)
);

-- Create index for searching trips by route
CREATE INDEX idx_trips_route_id ON trips(route_id);
CREATE INDEX idx_trips_service_id ON trips(service_id);

-- Stop times (train schedules at each station)
CREATE TABLE stop_times (
    trip_id varchar(191) NOT NULL,
    arrival_time varchar(255) NOT NULL,
    departure_time varchar(255) NOT NULL,
    stop_id varchar(255) NOT NULL,
    stop_sequence INTEGER NOT NULL,
    stop_headsign varchar(255),
    pickup_type INTEGER,
    drop_off_type INTEGER,
    shape_dist_traveled REAL,
    timepoint INTEGER,
    PRIMARY KEY (trip_id, stop_sequence),
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id),
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
);

-- Create indexes for searching stop times
CREATE INDEX idx_stop_times_trip_id ON stop_times(trip_id);
CREATE INDEX idx_stop_times_stop_id ON stop_times(stop_id);
CREATE INDEX idx_stop_times_arrival ON stop_times(arrival_time);
CREATE INDEX idx_stop_times_departure ON stop_times(departure_time);

-- Transfers between stops
CREATE TABLE transfers (
    from_stop_id varchar(255) NOT NULL,
    to_stop_id varchar(255) NOT NULL,
    transfer_type INTEGER NOT NULL,
    min_transfer_time INTEGER,
    PRIMARY KEY (from_stop_id, to_stop_id),
    FOREIGN KEY (from_stop_id) REFERENCES stops(stop_id),
    FOREIGN KEY (to_stop_id) REFERENCES stops(stop_id)
);

-- Translations for multilingual support
CREATE TABLE translations (
    trans_id varchar(255) NOT NULL,
    lang varchar(255) NOT NULL,
    translation varchar(255) NOT NULL,
    PRIMARY KEY (trans_id, lang)
);

-- ------------------------------------------------
-- Table structure for GTFS real-time data
-- ------------------------------------------------

-- Track/platform changes
CREATE TABLE track_changes (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    trip_id varchar(255) NOT NULL,
    stop_id varchar(255) NOT NULL,
    scheduled_track varchar(255),
    actual_track varchar(255),
    update_time TIMESTAMP NOT NULL,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id),
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
);

-- Realtime vehicle positions
CREATE TABLE vehicle_positions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    trip_id varchar(255) NOT NULL,
    vehicle_id varchar(255),
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    bearing REAL,
    speed REAL,
    current_stop_sequence INTEGER,
    current_status INTEGER,
    timestamp TIMESTAMP NOT NULL,
    congestion_level INTEGER,
    occupancy_status INTEGER,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
);

-- Trip updates
CREATE TABLE trip_updates (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    trip_id varchar(255) NOT NULL,
    route_id varchar(255) NOT NULL,
    schedule_relationship INTEGER,
    timestamp TIMESTAMP NOT NULL
);

-- Stop time updates
CREATE TABLE stop_time_updates (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    trip_update_id INTEGER NOT NULL,
    stop_sequence INTEGER,
    stop_id varchar(191) NOT NULL,
    arrival_delay INTEGER,
    arrival_time TIMESTAMP,
    departure_delay INTEGER,
    departure_time TIMESTAMP,
    schedule_relationship INTEGER,
    FOREIGN KEY (trip_update_id) REFERENCES trip_updates(id),
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
);

-- Table to keep track of data update timestamps
CREATE TABLE data_updates (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    data_type varchar(255) NOT NULL,
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    filename varchar(255),
    url varchar(255),
    status varchar(255)
);

-- The modification of last_updated column has been moved to the beginning of the file
ALTER TABLE data_updates MODIFY last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Create view for station information
CREATE VIEW station_view AS
SELECT 
    s.stop_id,
    s.stop_name,
    s.stop_lat,
    s.stop_lon,
    s.platform_code,
    COUNT(DISTINCT st.trip_id) as daily_trains
FROM 
    stops s
LEFT JOIN 
    stop_times st ON s.stop_id = st.stop_id
WHERE 
    s.location_type = 0
    AND (s.parent_station IS NULL OR s.parent_station = '')
GROUP BY 
    s.stop_id, s.stop_name, s.stop_lat, s.stop_lon, s.platform_code;

-- Create view for train schedules
CREATE VIEW train_schedule_view AS
SELECT 
    t.trip_id,
    r.route_short_name,
    t.trip_headsign,
    s.stop_name,
    st.departure_time,
    st.arrival_time,
    st.stop_sequence,
    s.platform_code
FROM 
    trips t
JOIN 
    routes r ON t.route_id = r.route_id
JOIN 
    stop_times st ON t.trip_id = st.trip_id
JOIN 
    stops s ON st.stop_id = s.stop_id
ORDER BY 
    t.trip_id, st.stop_sequence;