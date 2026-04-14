import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:audio_service/audio_service.dart';
import '../models/station.dart';

class AudioPlayerHandler extends BaseAudioHandler {
  final _player = AudioPlayer();
  String _currentUrl = '';
  bool _isPaused = false;
  Station? currentStation;

  AudioPlayerHandler() {
    // Forward just_audio state to audio_service's playbackState
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
  }

  Stream<PlayerState> get playerStateStream => _player.playerStateStream;

  Future<void> playStation(Station station) async {
    _currentUrl = station.urlResolved;
    currentStation = station;
    _isPaused = false;

    // Update media notification
    mediaItem.add(MediaItem(
      id: station.urlResolved,
      title: station.name,
      artist: station.country,
    ));

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
    currentStation = null;
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

  void dispose() {
    _player.dispose();
  }
}
