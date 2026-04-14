import 'package:uuid/uuid.dart';

class Station {
  final String stationuuid;
  final String name;
  final String urlResolved;
  final String country;
  final String countrycode;
  final String tags;
  final int bitrate;
  final bool isCustom;

  Station({
    required this.stationuuid,
    required this.name,
    required this.urlResolved,
    this.country = '',
    this.countrycode = '',
    this.tags = '',
    this.bitrate = 0,
    this.isCustom = false,
  });

  factory Station.fromJson(Map<String, dynamic> json) {
    return Station(
      stationuuid: json['stationuuid'] ?? '',
      name: json['name'] ?? 'Unknown',
      urlResolved: json['url_resolved'] ?? json['url'] ?? '',
      country: json['country'] ?? '',
      countrycode: json['countrycode'] ?? '',
      tags: json['tags'] ?? '',
      bitrate: json['bitrate'] ?? 0,
      isCustom: json['is_custom'] ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'stationuuid': stationuuid,
        'name': name,
        'url_resolved': urlResolved,
        'country': country,
        'countrycode': countrycode,
        'tags': tags,
        'bitrate': bitrate,
        'is_custom': isCustom,
      };

  factory Station.custom(String name, String url) {
    return Station(
      stationuuid: 'custom-${const Uuid().v4().substring(0, 12)}',
      name: name,
      urlResolved: url,
      country: 'Custom',
      tags: 'custom',
      isCustom: true,
    );
  }
}
