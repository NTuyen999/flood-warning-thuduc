import 'package:flutter/material.dart';
import 'core/risk_colors.dart';
import 'data/models/forecast.dart';
import 'data/models/road_segment.dart';
import 'data/services/mock_api_service.dart';

void main() => runApp(const MockCheckApp());

class MockCheckApp extends StatelessWidget {
  const MockCheckApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: MockCheckScreen(),
    );
  }
}

class MockCheckScreen extends StatelessWidget {
  const MockCheckScreen({super.key});

  Future<(List<RoadSegment>, Forecast)> _load() async {
    final api = MockApiService();
    final segs = await api.getRoadSegments();
    final fc = await api.getForecast(segs.first.id);
    return (segs, fc);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Test mock data')),
      body: FutureBuilder(
        future: _load(),
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(child: Text('Lỗi: ${snap.error}'));
          }
          final (segs, fc) = snap.data!;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('Số đoạn đường: ${segs.length}'),
              for (final s in segs)
                Text('${s.id} - ${s.name} (${s.points.length} điểm)'),
              const SizedBox(height: 16),
              Text('Forecast ${fc.segmentId} - mock: ${fc.isMock}'),
              for (final h in fc.horizons)
                ListTile(
                  leading: CircleAvatar(backgroundColor: riskColor(h.level)),
                  title: Text('+${h.h}h'),
                  subtitle: Text(
                      '${(h.probability * 100).toStringAsFixed(0)}% (${h.level})'),
                ),
            ],
          );
        },
      ),
    );
  }
}