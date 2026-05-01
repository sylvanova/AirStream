import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:audio_service/audio_service.dart';
import '../models/station.dart';

class AudioPlayerHandler extends BaseAudioHandler {
  final _player = AudioPlayer();
  final _songController = StreamController<String>.broadcast();

  String _currentUrl = '';
  bool _isPaused = false;
  Station? currentStation;
  String _currentSong = '';

  AudioPlayerHandler() {
    // Forward just_audio state to audio_service's playbackState.
    _player.playerStateStream.listen((state) {
      if (_isPaused) return;
      final playing = state.playing;
      final processingState = switch (state.processingState) {
        ProcessingState.idle => AudioProcessingState.idle,
        ProcessingState.loading => AudioProcessingState.loading,
        ProcessingState.buffering => AudioProcessingState.buffering,
        ProcessingState.ready => AudioProcessingState.ready,
        ProcessingState.completed => AudioProcessingState.completed,
      };
      playbackState.add(playbackState.value.copyWith(
        controls: [
          if (playing) MediaControl.pause else MediaControl.play,
          MediaControl.stop,
        ],
        systemActions: const {MediaAction.play, MediaAction.pause, MediaAction.stop},
        playing: playing,
        processingState: processingState,
      ));
    });

    // ICY metadata for live streams: extract StreamTitle and surface it.
    // Only process events that carry actual metadata (non-null info).
    _player.icyMetadataStream.listen((event) {
      if (event == null || event.info == null) return;
      final title = event.info!.title?.trim() ?? '';
      _handleIcyTitle(title);
    });
  }

  Stream<PlayerState> get playerStateStream => _player.playerStateStream;

  /// Stream of the current song title. Emits '' when no song is known.
  Stream<String> get currentSongStream => _songController.stream;

  String get currentSong => _currentSong;

  Future<void> playStation(Station station) async {
    _currentUrl = station.urlResolved;
    currentStation = station;
    _isPaused = false;
    _resetSongFor(station);

    try {
      await _player.setAudioSource(
        AudioSource.uri(Uri.parse(station.urlResolved)),
      );
      await _player.play();
    } catch (e) {
      debugPrint('AIRSTREAM: retrying with headers: $e');
      await _player.setAudioSource(
        AudioSource.uri(
          Uri.parse(station.urlResolved),
          headers: {'User-Agent': 'AirStream/1.0'},
        ),
      );
      await _player.play();
    }
  }

  @override
  Future<void> play() async {
    if (_isPaused && _currentUrl.isNotEmpty) {
      _isPaused = false;
      await _player.setUrl(_currentUrl);
      await _player.play();
    }
  }

  @override
  Future<void> pause() async {
    _isPaused = true;
    await _player.stop();
    playbackState.add(playbackState.value.copyWith(
      controls: [MediaControl.play, MediaControl.stop],
      systemActions: const {MediaAction.play, MediaAction.pause, MediaAction.stop},
      playing: false,
      processingState: AudioProcessingState.ready,
    ));
  }

  @override
  Future<void> stop() async {
    _isPaused = false;
    _currentUrl = '';
    final hadStation = currentStation != null;
    currentStation = null;
    if (hadStation) {
      _currentSong = '';
      _songController.add('');
    }
    await _player.stop();
    playbackState.add(playbackState.value.copyWith(
      controls: [],
      playing: false,
      processingState: AudioProcessingState.idle,
    ));
    await super.stop();
  }

  bool get isPaused => _isPaused;
  bool get isPlaying => _player.playing && !_isPaused;
  String get currentUrl => _currentUrl;

  void _resetSongFor(Station station) {
    _currentSong = '';
    _songController.add('');
    mediaItem.add(MediaItem(
      id: station.urlResolved,
      title: station.name,
      artist: station.country,
    ));
  }

  void _handleIcyTitle(String title) {
    if (title == _currentSong) return;
    _currentSong = title;
    _songController.add(title);
    final station = currentStation;
    if (station == null) return;
    if (title.isNotEmpty) {
      mediaItem.add(MediaItem(
        id: station.urlResolved,
        title: title,
        artist: station.name,
      ));
    } else {
      mediaItem.add(MediaItem(
        id: station.urlResolved,
        title: station.name,
        artist: station.country,
      ));
    }
  }

  // ---- test hooks --------------------------------------------------------

  @visibleForTesting
  void debugResetSongFor(Station station) {
    currentStation = station;
    _resetSongFor(station);
  }

  @visibleForTesting
  void debugHandleIcyTitle(String title) {
    _handleIcyTitle(title);
  }

  // ---- lifecycle ---------------------------------------------------------

  void dispose() {
    _songController.close();
    _player.dispose();
  }
}
