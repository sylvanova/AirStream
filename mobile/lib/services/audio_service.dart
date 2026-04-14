import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import '../models/station.dart';

class AudioPlayerHandler {
  final _player = AudioPlayer();
  String _currentUrl = '';
  bool _isPaused = false;
  Station? currentStation;

  Stream<PlayerState> get playerStateStream => _player.playerStateStream;

  Future<void> playStation(Station station) async {
    _currentUrl = station.urlResolved;
    currentStation = station;
    _isPaused = false;
    try {
      await _player.setAudioSource(
        AudioSource.uri(Uri.parse(station.urlResolved)),
      );
      await _player.play();
    } catch (e) {
      debugPrint('AIRSTREAM: setUrl failed, retrying with headers: $e');
      // Some streams need a user-agent header
      await _player.setAudioSource(
        AudioSource.uri(
          Uri.parse(station.urlResolved),
          headers: {'User-Agent': 'AirStream/1.0'},
        ),
      );
      await _player.play();
    }
  }

  Future<void> play() async {
    if (_isPaused && _currentUrl.isNotEmpty) {
      _isPaused = false;
      await _player.setUrl(_currentUrl);
      await _player.play();
    }
  }

  Future<void> pause() async {
    _isPaused = true;
    await _player.stop();
  }

  Future<void> stop() async {
    _isPaused = false;
    _currentUrl = '';
    currentStation = null;
    await _player.stop();
  }

  bool get isPaused => _isPaused;
  bool get isPlaying => _player.playing && !_isPaused;
  String get currentUrl => _currentUrl;

  void dispose() {
    _player.dispose();
  }
}
