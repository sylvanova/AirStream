import 'package:flutter/material.dart';
import 'package:audio_service/audio_service.dart';
import 'services/audio_service.dart';
import 'screens/home_screen.dart';

late AudioPlayerHandler audioHandler;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    audioHandler = await AudioService.init(
      builder: () => AudioPlayerHandler(),
      config: const AudioServiceConfig(
        androidNotificationChannelId: 'com.airstream.airstream.channel.audio',
        androidNotificationChannelName: 'AirStream',
        androidNotificationOngoing: true,
      ),
    );
  } catch (e) {
    debugPrint('AIRSTREAM: AudioService.init failed: $e, using fallback');
    audioHandler = AudioPlayerHandler();
  }
  runApp(const AirStreamApp());
}

class AirStreamApp extends StatelessWidget {
  const AirStreamApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AirStream',
      theme: ThemeData(
        colorSchemeSeed: Colors.deepPurple,
        useMaterial3: true,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: Colors.deepPurple,
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      home: HomeScreen(audioHandler: audioHandler),
    );
  }
}
