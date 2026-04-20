import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/station.dart';

class StorageService {
  // Favorites are stored as a JSON list of full Station objects. Legacy data
  // stored only UUIDs; we migrate on first read by hydrating from the cached
  // station list. UUIDs that can't be hydrated locally are kept as stub
  // Stations (name "Loading…") and picked up by rehydrateFavorites() so the
  // user doesn't lose them.
  static const _favoritesKey = 'favorites';
  static const _stubName = 'Loading…';

  static Future<List<Station>> _readFavorites() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_favoritesKey);
    if (raw == null) return [];
    final decoded = jsonDecode(raw);
    if (decoded is! List) return [];
    if (decoded.isEmpty) return [];

    if (decoded.first is String) {
      // Legacy format: list of UUID strings. Hydrate from cache.
      final uuids = List<String>.from(decoded);
      final cached = await getCachedStations();
      final byUuid = {for (final s in cached) s.stationuuid: s};
      final migrated = uuids
          .map((u) => byUuid[u] ??
              Station(stationuuid: u, name: _stubName, urlResolved: ''))
          .toList();
      await _writeFavorites(migrated);
      return migrated;
    }

    return (decoded as List<dynamic>)
        .map((j) => Station.fromJson(Map<String, dynamic>.from(j)))
        .toList();
  }

  static Future<void> _writeFavorites(List<Station> favorites) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
        _favoritesKey, jsonEncode(favorites.map((s) => s.toJson()).toList()));
  }

  static Future<List<Station>> getFavorites() => _readFavorites();

  static Future<List<String>> getFavoriteUuids() async {
    final favs = await _readFavorites();
    return favs.map((s) => s.stationuuid).toList();
  }

  static Future<void> addFavorite(Station station) async {
    final favs = await _readFavorites();
    if (favs.any((s) => s.stationuuid == station.stationuuid)) return;
    favs.add(station);
    await _writeFavorites(favs);
  }

  static Future<void> removeFavorite(String uuid) async {
    final favs = await _readFavorites();
    favs.removeWhere((s) => s.stationuuid == uuid);
    await _writeFavorites(favs);
  }

  static Future<bool> isFavorite(String uuid) async {
    final favs = await _readFavorites();
    return favs.any((s) => s.stationuuid == uuid);
  }

  static Future<List<String>> pendingFavoriteUuids() async {
    final favs = await _readFavorites();
    return favs
        .where((s) => s.name == _stubName)
        .map((s) => s.stationuuid)
        .toList();
  }

  static Future<void> rehydrateFavorites(List<Station> fresh) async {
    if (fresh.isEmpty) return;
    final byUuid = {for (final s in fresh) s.stationuuid: s};
    final favs = await _readFavorites();
    var changed = false;
    for (var i = 0; i < favs.length; i++) {
      final replacement = byUuid[favs[i].stationuuid];
      if (replacement != null && favs[i].name == _stubName) {
        favs[i] = replacement;
        changed = true;
      }
    }
    if (changed) await _writeFavorites(favs);
  }

  static Future<List<Station>> getCustomStations() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('custom_stations');
    if (raw == null) return [];
    final list = jsonDecode(raw) as List<dynamic>;
    return list.map((j) => Station.fromJson(j)).toList();
  }

  static Future<Station> addCustomStation(String name, String url) async {
    final stations = await getCustomStations();
    final station = Station.custom(name, url);
    stations.add(station);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
        'custom_stations', jsonEncode(stations.map((s) => s.toJson()).toList()));
    return station;
  }

  static Future<void> removeCustomStation(String uuid) async {
    final stations = await getCustomStations();
    stations.removeWhere((s) => s.stationuuid == uuid);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
        'custom_stations', jsonEncode(stations.map((s) => s.toJson()).toList()));
  }

  static Future<void> saveCachedStations(List<Station> stations) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
        'cached_stations', jsonEncode(stations.map((s) => s.toJson()).toList()));
  }

  static Future<List<Station>> getCachedStations() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('cached_stations');
    if (raw == null) return [];
    final list = jsonDecode(raw) as List<dynamic>;
    return list.map((j) => Station.fromJson(j)).toList();
  }
}
