import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/station.dart';

class RadioApi {
  static const _servers = [
    'https://de1.api.radio-browser.info',
    'https://nl1.api.radio-browser.info',
  ];
  static const _timeout = Duration(seconds: 10);

  static Future<List<dynamic>> _get(String path,
      {Map<String, String>? params}) async {
    for (final server in _servers) {
      try {
        final uri = Uri.parse('$server$path').replace(queryParameters: params);
        final response = await http
            .get(uri, headers: {'User-Agent': 'AirStream/1.0'}).timeout(
                _timeout);
        if (response.statusCode == 200) {
          return jsonDecode(response.body) as List<dynamic>;
        }
      } catch (_) {
        continue;
      }
    }
    return [];
  }

  static Future<List<Station>> fetchTopStations({int limit = 100}) async {
    final data =
        await _get('/json/stations/topclick/$limit', params: {'hidebroken': 'true'});
    return data.map((j) => Station.fromJson(j)).toList();
  }

  static Future<List<Station>> searchStations({
    String name = '',
    String countrycode = '',
    String tag = '',
    int limit = 100,
  }) async {
    final params = <String, String>{
      'order': 'clickcount',
      'reverse': 'true',
      'limit': '$limit',
      'hidebroken': 'true',
    };
    if (name.isNotEmpty) params['name'] = name;
    if (countrycode.isNotEmpty) params['countrycode'] = countrycode;
    if (tag.isNotEmpty) params['tag'] = tag;

    final data = await _get('/json/stations/search', params: params);
    return data.map((j) => Station.fromJson(j)).toList();
  }

  static Future<List<Map<String, dynamic>>> fetchCountries(
      {int limit = 50}) async {
    final data = await _get('/json/countries', params: {
      'order': 'stationcount',
      'reverse': 'true',
      'limit': '$limit',
    });
    return data.cast<Map<String, dynamic>>();
  }

  static Future<List<Map<String, dynamic>>> fetchTags(
      {int limit = 50}) async {
    final data = await _get('/json/tags', params: {
      'order': 'stationcount',
      'reverse': 'true',
      'limit': '$limit',
    });
    return data.cast<Map<String, dynamic>>();
  }
}
