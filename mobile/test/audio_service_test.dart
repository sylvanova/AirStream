import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:audio_service/audio_service.dart';
import 'package:airstream/services/audio_service.dart';
import 'package:airstream/models/station.dart';

class _Recorder<T> {
  final List<T> events = [];
  late final StreamSubscription<T> sub;
  _Recorder(Stream<T> s) {
    sub = s.listen(events.add);
  }
  void cancel() => sub.cancel();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('currentSongStream emits empty string initially after playStation', () async {
    final handler = AudioPlayerHandler();
    final station = Station(
      stationuuid: 'uuid-1',
      name: 'Soma FM',
      urlResolved: 'http://example.com/stream',
      country: 'USA',
    );

    final rec = _Recorder<String>(handler.currentSongStream);
    handler.debugResetSongFor(station);

    await Future<void>.delayed(const Duration(milliseconds: 10));
    expect(rec.events, contains(''));
    rec.cancel();
  });

  test('handleIcyTitle updates currentSongStream and mediaItem', () async {
    final handler = AudioPlayerHandler();
    final station = Station(
      stationuuid: 'uuid-1',
      name: 'Soma FM',
      urlResolved: 'http://example.com/stream',
      country: 'USA',
    );
    handler.debugResetSongFor(station);

    final rec = _Recorder<String>(handler.currentSongStream);
    final mediaRec = _Recorder<MediaItem?>(handler.mediaItem);

    handler.debugHandleIcyTitle('Tycho - A Walk');
    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(rec.events.last, 'Tycho - A Walk');
    expect(mediaRec.events.last?.title, 'Tycho - A Walk');
    expect(mediaRec.events.last?.artist, 'Soma FM');

    rec.cancel();
    mediaRec.cancel();
  });

  test('handleIcyTitle dedupes identical titles', () async {
    final handler = AudioPlayerHandler();
    final station = Station(
      stationuuid: 'uuid-1',
      name: 'Soma FM',
      urlResolved: 'http://example.com/stream',
      country: 'USA',
    );
    handler.debugResetSongFor(station);

    final rec = _Recorder<String>(handler.currentSongStream);
    handler.debugHandleIcyTitle('Tycho - A Walk');
    handler.debugHandleIcyTitle('Tycho - A Walk');
    handler.debugHandleIcyTitle('Tycho - A Walk');

    await Future<void>.delayed(const Duration(milliseconds: 10));

    final tychoCount = rec.events.where((e) => e == 'Tycho - A Walk').length;
    expect(tychoCount, 1);
    rec.cancel();
  });

  test('handleIcyTitle empty title falls back to station as MediaItem title', () async {
    final handler = AudioPlayerHandler();
    final station = Station(
      stationuuid: 'uuid-1',
      name: 'Soma FM',
      urlResolved: 'http://example.com/stream',
      country: 'USA',
    );
    handler.debugResetSongFor(station);

    final mediaRec = _Recorder<MediaItem?>(handler.mediaItem);
    handler.debugHandleIcyTitle('Tycho - A Walk');
    handler.debugHandleIcyTitle('');

    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(mediaRec.events.last?.title, 'Soma FM');
    expect(mediaRec.events.last?.artist, 'USA');
    mediaRec.cancel();
  });
}
