import 'package:flutter/material.dart';
import 'features/map/map_screen.dart';

void main() => runApp(const FloodApp());

class FloodApp extends StatelessWidget {
  const FloodApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Cảnh báo nguy cơ mưa lớn - Thủ Đức',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.blue, useMaterial3: true),
      home: const MapScreen(),
    );
  }
}