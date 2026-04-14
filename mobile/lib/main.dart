import 'package:flutter/material.dart';
import 'services/audio_service.dart';
import 'screens/home_screen.dart';

late AudioPlayerHandler audioHandler;

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  audioHandler = AudioPlayerHandler();
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
