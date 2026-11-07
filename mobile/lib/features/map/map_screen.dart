import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../data/models/road_segment.dart';
import '../../data/services/api.dart';
import '../forecast/forecast_screen.dart';
import '../report/history_screen.dart';
import '../report/report_screen.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final LayerHitNotifier<String> _hit = ValueNotifier(null);
  late Future<List<RoadSegment>> _future = api.getRoadSegments();

  @override
  void dispose() {
    _hit.dispose();
    super.dispose();
  }

  void _retry() => setState(() => _future = api.getRoadSegments());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bản đồ nguy cơ'),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () => Navigator.push(context,
                MaterialPageRoute(builder: (_) => const HistoryScreen())),
          ),
        ],
      ),
      body: FutureBuilder<List<RoadSegment>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text('Không tải được đoạn đường\n${snap.error}',
                    textAlign: TextAlign.center),
                const SizedBox(height: 12),
                FilledButton(onPressed: _retry, child: const Text('Thử lại')),
              ]),
            );
          }
          final segs = snap.data!;
          if (segs.isEmpty) {
            return const Center(child: Text('Chưa có đoạn đường nào'));
          }
          return Stack(children: [
            FlutterMap(
              options: MapOptions(
                initialCenter: LatLng(10.85, 106.77),
                initialZoom: 12.5,
              ),
              children: [
                TileLayer(
                  urlTemplate:
                  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
                  userAgentPackageName: 'com.example.mobile',
                ),
                GestureDetector(
                  onTap: () {
                    final id = _hit.value?.hitValues.firstOrNull;
                    if (id == null) return;
                    final seg = segs.firstWhere((s) => s.id == id);
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => ForecastScreen(segment: seg)),
                    );
                  },
                  child: PolylineLayer<String>(
                    hitNotifier: _hit,
                    polylines: [
                      for (final s in segs)
                        Polyline<String>(
                          points: s.points,
                          strokeWidth: 8,
                          color: Colors.blueGrey,
                          hitValue: s.id,
                        ),
                    ],
                  ),
                ),
              ],
            ),
            const Positioned(
              left: 12,
              bottom: 12,
              child: Card(
                child: Padding(
                  padding: EdgeInsets.all(8),
                  child: Text('Chạm vào một đoạn đường để xem dự báo'),
                ),
              ),
            ),
          ]);
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.add),
        label: const Text('Báo cáo'),
        onPressed: () => Navigator.push(
            context, MaterialPageRoute(builder: (_) => const ReportScreen())),
      ),
    );
  }
}