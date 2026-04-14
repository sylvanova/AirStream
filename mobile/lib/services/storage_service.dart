import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/station.dart';

class StorageService {
  static Future<List<String>> getFavorites() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('favorites');
    if (raw == null) return [];
    return List<String>.from(jsonDecode(raw));
  }

  static Future<void> addFavorite(String uuid) async {
    final favs = await getFavorites();
    if (!favs.contains(uuid)) {
      favs.add(uuid);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('favorites', jsonEncode(favs));
    }
  }

  static Future<void> removeFavorite(String uuid) async {
    final favs = await getFavorites();
    favs.remove(uuid);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('favorites', jsonEncode(favs));
  }

  static Future<bool> isFavorite(String uuid) async {
    final favs = await getFavorites();
    return favs.contains(uuid);
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
