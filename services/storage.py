import json
import os
import uuid


def _data_path():
    home = os.path.expanduser("~")
    directory = os.path.join(home, ".airstream")
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "data.json")


def _default_data():
    return {
        "favorites": [],
        "custom_stations": [],
    }


def load_data():
    path = _data_path()
    if not os.path.exists(path):
        return _default_data()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "favorites" not in data:
            data["favorites"] = []
        if "custom_stations" not in data:
            data["custom_stations"] = []
        return data
    except (json.JSONDecodeError, OSError):
        return _default_data()


def save_data(data):
    path = _data_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_favorite(station_uuid):
    data = load_data()
    if station_uuid not in data["favorites"]:
        data["favorites"].append(station_uuid)
        save_data(data)


def remove_favorite(station_uuid):
    data = load_data()
    if station_uuid in data["favorites"]:
        data["favorites"].remove(station_uuid)
        save_data(data)


def is_favorite(station_uuid):
    data = load_data()
    return station_uuid in data["favorites"]


def get_favorites():
    return load_data()["favorites"]


def add_custom_station(name, url):
    data = load_data()
    station = {
        "stationuuid": f"custom-{uuid.uuid4().hex[:12]}",
        "name": name,
        "url_resolved": url,
        "country": "Custom",
        "tags": "custom",
        "bitrate": 0,
        "is_custom": True,
    }
    data["custom_stations"].append(station)
    save_data(data)
    return station


def remove_custom_station(station_uuid):
    data = load_data()
    data["custom_stations"] = [
        s for s in data["custom_stations"] if s["stationuuid"] != station_uuid
    ]
    save_data(data)


def get_custom_stations():
    return load_data()["custom_stations"]


def save_cached_stations(stations):
    data = load_data()
    data["cached_stations"] = stations
    save_data(data)


def get_cached_stations():
    data = load_data()
    return data.get("cached_stations", [])
