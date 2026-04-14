import requests

SERVERS = [
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
]
TIMEOUT = 10
USER_AGENT = "AirStream/1.0"


def _get(path, params=None):
    headers = {"User-Agent": USER_AGENT}
    for server in SERVERS:
        try:
            resp = requests.get(
                f"{server}{path}",
                params=params,
                headers=headers,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError):
            continue
    return []


def fetch_top_stations(limit=100):
    return _get(f"/json/stations/topclick/{limit}", {"hidebroken": "true"})


def search_stations(name="", countrycode="", tag="", limit=100):
    params = {
        "order": "clickcount",
        "reverse": "true",
        "limit": str(limit),
        "hidebroken": "true",
    }
    if name:
        params["name"] = name
    if countrycode:
        params["countrycode"] = countrycode
    if tag:
        params["tag"] = tag
    return _get("/json/stations/search", params)


def fetch_countries(limit=50):
    return _get("/json/countries", {
        "order": "stationcount",
        "reverse": "true",
        "limit": str(limit),
    })


def fetch_tags(limit=50):
    return _get("/json/tags", {
        "order": "stationcount",
        "reverse": "true",
        "limit": str(limit),
    })


def fetch_stations_by_uuid(uuids):
    if not uuids:
        return []
    return _get("/json/stations/byuuid", {"uuids": ",".join(uuids)})
