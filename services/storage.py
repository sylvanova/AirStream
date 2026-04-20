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


def _migrate_favorites(data):
    # Legacy format: favorites was a list of UUID strings. Hydrate from the
    # cached station list where possible; UUIDs that can't be hydrated here are
    # kept as stub entries so the view can show them and the app can rehydrate
    # them via the API on next startup.
    favs = data.get("favorites", [])
    if not favs or not isinstance(favs[0], str):
        return data

    cached = {s.get("stationuuid"): s for s in data.get("cached_stations", [])}
    new_favs = []
    for station_uuid in favs:
        station = cached.get(station_uuid)
        if station:
            new_favs.append(station)
        else:
            new_favs.append({
                "stationuuid": station_uuid,
                "name": "Loading…",
                "_needs_rehydrate": True,
            })
    data["favorites"] = new_favs
    return data


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
        data = _migrate_favorites(data)
        return data
    except (json.JSONDecodeError, OSError):
        return _default_data()


def save_data(data):
    path = _data_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_favorite(station):
    if not isinstance(station, dict):
        return
    station_uuid = station.get("stationuuid")
    if not station_uuid:
        return
    data = load_data()
    for existing in data["favorites"]:
        if existing.get("stationuuid") == station_uuid:
            return
    data["favorites"].append(station)
    save_data(data)


def remove_favorite(station_uuid):
    data = load_data()
    data["favorites"] = [
        s for s in data["favorites"] if s.get("stationuuid") != station_uuid
    ]
    save_data(data)


def is_favorite(station_uuid):
    data = load_data()
    return any(s.get("stationuuid") == station_uuid for s in data["favorites"])


def get_favorites():
    return load_data()["favorites"]


def pending_favorite_uuids():
    return [
        s.get("stationuuid")
        for s in get_favorites()
        if s.get("_needs_rehydrate") and s.get("stationuuid")
    ]


def update_favorites_with_stations(stations):
    if not stations:
        return
    by_uuid = {s.get("stationuuid"): s for s in stations if s.get("stationuuid")}
    data = load_data()
    changed = False
    for i, fav in enumerate(data["favorites"]):
        fresh = by_uuid.get(fav.get("stationuuid"))
        if fresh and fav.get("_needs_rehydrate"):
            data["favorites"][i] = fresh
            changed = True
    if changed:
        save_data(data)


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


def get_volume(default=100):
    value = load_data().get("volume")
    if isinstance(value, (int, float)) and 0 <= value <= 100:
        return int(value)
    return default


def set_volume(percent):
    data = load_data()
    data["volume"] = max(0, min(100, int(percent)))
    save_data(data)


def save_cached_stations(stations):
    data = load_data()
    data["cached_stations"] = stations
    save_data(data)


def get_cached_stations():
    data = load_data()
    return data.get("cached_stations", [])
