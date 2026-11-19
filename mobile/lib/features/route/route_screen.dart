import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../core/demo_mode.dart';
import '../../core/risk_colors.dart';
import '../../core/widgets.dart';
import '../../data/models/demo.dart';
import '../../data/services/api.dart';

class RouteScreen extends StatefulWidget {
  final String? initialFrom;
  final String? initialTo;

  const RouteScreen({super.key, this.initialFrom, this.initialTo});

  @override
  State<RouteScreen> createState() => _RouteScreenState();
}

class _RouteScreenState extends State<RouteScreen> {
  final _mapController = MapController();
  List<RoutePoint> _points = [];
  bool _loadingPoints = true;
  String? _fromPoint;
  String? _toPoint;
  RouteResult? _result;
  bool _loadingRoute = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    demoMode.addListener(_onDemoModeChanged);
    _loadPoints();
  }

  @override
  void dispose() {
    demoMode.removeListener(_onDemoModeChanged);
    _mapController.dispose();
    super.dispose();
  }

  void _onDemoModeChanged() {
    if (_fromPoint != null && _toPoint != null) {
      _findRoute();
    }
  }

  Future<void> _loadPoints() async {
    try {
      final points = await api.getDemoRoutePoints();
      if (!mounted) return;
      setState(() {
        _points = points;
        _loadingPoints = false;

        // Set default selection
        if (points.isNotEmpty) {
          _fromPoint = widget.initialFrom ?? (points.any((p) => p.id == 'P1') ? 'P1' : points.first.id);
          _toPoint = widget.initialTo ?? (points.any((p) => p.id == 'J2') ? 'J2' : points.last.id);
        }
      });
      _findRoute();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loadingPoints = false;
      });
    }
  }

  Future<void> _findRoute() async {
    if (_fromPoint == null || _toPoint == null) return;
    setState(() {
      _loadingRoute = true;
      _error = null;
    });

    try {
      final result = await api.getDemoRoute(
        scenario: demoMode.value.scenario,
        fromPoint: _fromPoint!,
        toPoint: _toPoint!,
      );
      if (!mounted) return;
      setState(() {
        _result = result;
        _loadingRoute = false;
      });

      // Fit camera to route
      final rec = result.recommended;
      final short = result.shortest;
      final coords = rec?.geometry ?? short?.geometry ?? [];
      if (coords.isNotEmpty) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _mapController.fitCamera(CameraFit.coordinates(
            coordinates: coords,
            padding: const EdgeInsets.all(40),
          ));
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loadingRoute = false;
      });
    }
  }

  Widget _buildStatusHeader(RouteResult res) {
    final (icon, color, label) = switch (res.status) {
      'ok' => (Icons.check_circle_outline, const Color(0xFF2E9E5B), 'Tuyến thông suốt'),
      'detour' => (Icons.alt_route, const Color(0xFFE5A800), 'Đường vòng tránh ngập'),
      'warning' => (Icons.warning_amber_rounded, const Color(0xFFF07C1B), 'Cảnh báo hẻm ngập'),
      _ => (Icons.block, const Color(0xFFD93025), 'Không thể di chuyển'),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              label,
              style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16),
            ),
          ),
          Pill(Icons.layers, demoScenarioLabel(res.scenario), Colors.blueGrey),
        ],
      ),
    );
  }

  String demoScenarioLabel(String id) => switch (id) {
        'none' => 'Không mưa',
        'moderate' => 'Mưa vừa',
        _ => 'Mưa nhiều',
      };

  @override
  Widget build(BuildContext context) {
    final res = _result;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Gợi ý đường đi (Mô phỏng)'),
      ),
      body: ValueListenableBuilder<DemoState>(
        valueListenable: demoMode,
        builder: (context, state, _) {
          return Column(
            children: [
              // Simulation Banner
              Container(
                width: double.infinity,
                color: Theme.of(context).colorScheme.tertiaryContainer,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                child: Row(
                  children: [
                    Icon(Icons.science,
                        size: 18, color: Theme.of(context).colorScheme.onTertiaryContainer),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'ĐANG XEM DỮ LIỆU MÔ PHỎNG – không phải dự báo thật',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Theme.of(context).colorScheme.onTertiaryContainer,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Controls Card
              Card(
                margin: const EdgeInsets.all(12),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Scenario Chip Selector
                      Row(
                        children: [
                          const Text('Kịch bản:', style: TextStyle(fontWeight: FontWeight.bold)),
                          const SizedBox(width: 8),
                          Expanded(
                            child: SingleChildScrollView(
                              scrollDirection: Axis.horizontal,
                              child: Row(
                                children: [
                                  for (final sc in [
                                    ('none', 'Không mưa'),
                                    ('moderate', 'Mưa vừa'),
                                    ('heavy', 'Mưa nhiều'),
                                  ])
                                    Padding(
                                      padding: const EdgeInsets.only(right: 6),
                                      child: ChoiceChip(
                                        label: Text(sc.$2),
                                        selected: state.scenario == sc.$1,
                                        onSelected: (_) {
                                          demoMode.setScenario(sc.$1);
                                          _findRoute();
                                        },
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),

                      // From - To Dropdowns
                      Row(
                        children: [
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              initialValue: _fromPoint,
                              isExpanded: true,
                              decoration: const InputDecoration(
                                labelText: 'Điểm đi',
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              items: [
                                for (final p in _points)
                                  DropdownMenuItem(
                                    value: p.id,
                                    child: Text(p.name, overflow: TextOverflow.ellipsis),
                                  ),
                              ],
                              onChanged: (val) {
                                if (val != null) {
                                  setState(() => _fromPoint = val);
                                  _findRoute();
                                }
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          const Icon(Icons.arrow_forward),
                          const SizedBox(width: 8),
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              initialValue: _toPoint,
                              isExpanded: true,
                              decoration: const InputDecoration(
                                labelText: 'Điểm đến',
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              items: [
                                for (final p in _points)
                                  DropdownMenuItem(
                                    value: p.id,
                                    child: Text(p.name, overflow: TextOverflow.ellipsis),
                                  ),
                              ],
                              onChanged: (val) {
                                if (val != null) {
                                  setState(() => _toPoint = val);
                                  _findRoute();
                                }
                              },
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),

              // Map & Results View
              Expanded(
                child: _loadingPoints || _loadingRoute
                    ? const Center(child: CircularProgressIndicator())
                    : _error != null
                        ? ErrorRetry(_error!, _findRoute)
                        : ListView(
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            children: [
                              if (res != null) ...[
                                _buildStatusHeader(res),
                                const SizedBox(height: 10),
                              ],

                              // Map
                              ClipRRect(
                                borderRadius: BorderRadius.circular(16),
                                child: SizedBox(
                                  height: 240,
                                  child: BaseMap(
                                    controller: _mapController,
                                    options: MapOptions(
                                      initialCenter: const LatLng(10.834, 106.728),
                                      initialZoom: 15,
                                    ),
                                    children: [
                                      // Shortest path (if different from recommended)
                                      if (res?.shortest != null &&
                                          res?.recommended != null &&
                                          res!.shortest!.geometry.isNotEmpty)
                                        PolylineLayer(
                                          polylines: [
                                            Polyline(
                                              points: res.shortest!.geometry,
                                              strokeWidth: 4,
                                              color: Colors.grey,
                                              pattern: StrokePattern.dashed(segments: [8.0, 6.0]),
                                            ),
                                          ],
                                        ),

                                      // Recommended path
                                      if (res?.recommended != null &&
                                          res!.recommended!.geometry.isNotEmpty)
                                        PolylineLayer(
                                          polylines: [
                                            Polyline(
                                              points: res.recommended!.geometry,
                                              strokeWidth: 6,
                                              color: Theme.of(context).colorScheme.primary,
                                            ),
                                          ],
                                        ),

                                      // Markers for Start and End Points
                                      MarkerLayer(
                                        markers: [
                                          for (final p in _points)
                                            if (p.id == _fromPoint || p.id == _toPoint)
                                              Marker(
                                                point: p.coordinates,
                                                width: 36,
                                                height: 36,
                                                child: DecoratedBox(
                                                  decoration: BoxDecoration(
                                                    color: p.id == _fromPoint
                                                        ? Colors.green
                                                        : Colors.red,
                                                    shape: BoxShape.circle,
                                                    border: Border.all(
                                                        color: Colors.white, width: 2),
                                                    boxShadow: const [
                                                      BoxShadow(
                                                          blurRadius: 4, color: Colors.black26)
                                                    ],
                                                  ),
                                                  child: Center(
                                                    child: Text(
                                                      p.id,
                                                      style: const TextStyle(
                                                          color: Colors.white,
                                                          fontWeight: FontWeight.bold,
                                                          fontSize: 12),
                                                    ),
                                                  ),
                                                ),
                                              ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),

                              const SizedBox(height: 12),

                              // Details Card
                              if (res != null) ...[
                                Card(
                                  child: Padding(
                                    padding: const EdgeInsets.all(14),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        if (res.recommended != null) ...[
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Column(
                                                  children: [
                                                    const Icon(Icons.straighten, color: Colors.blue),
                                                    const SizedBox(height: 4),
                                                    Text(
                                                      res.recommended!.lengthM >= 1000
                                                          ? '${(res.recommended!.lengthM / 1000).toStringAsFixed(2)} km'
                                                          : '${res.recommended!.lengthM.round()} m',
                                                      style: Theme.of(context).textTheme.titleMedium,
                                                      overflow: TextOverflow.ellipsis,
                                                    ),
                                                    Text('Quãng đường',
                                                        style: Theme.of(context).textTheme.bodySmall),
                                                  ],
                                                ),
                                              ),
                                              Expanded(
                                                child: Column(
                                                  children: [
                                                    const Icon(Icons.timer, color: Colors.amber),
                                                    const SizedBox(height: 4),
                                                    Text(
                                                      '${res.recommended!.etaMin} phút',
                                                      style: Theme.of(context).textTheme.titleMedium,
                                                      overflow: TextOverflow.ellipsis,
                                                    ),
                                                    Text('Thời gian ước tính*',
                                                        textAlign: TextAlign.center,
                                                        style: Theme.of(context).textTheme.bodySmall),
                                                  ],
                                                ),
                                              ),
                                              Expanded(
                                                child: Column(
                                                  children: [
                                                    Icon(riskIcon(res.recommended!.maxLevel),
                                                        color: riskColor(res.recommended!.maxLevel)),
                                                    const SizedBox(height: 4),
                                                    Text(
                                                      riskLabel(res.recommended!.maxLevel),
                                                      style: Theme.of(context).textTheme.titleMedium,
                                                      overflow: TextOverflow.ellipsis,
                                                    ),
                                                    Text('Nguy cơ tối đa',
                                                        textAlign: TextAlign.center,
                                                        style: Theme.of(context).textTheme.bodySmall),
                                                  ],
                                                ),
                                              ),
                                            ],
                                          ),
                                          const Divider(height: 24),
                                        ],

                                        // Messages
                                        for (final msg in res.messages)
                                          Padding(
                                            padding: const EdgeInsets.only(bottom: 6),
                                            child: Row(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                const Icon(Icons.info_outline,
                                                    size: 18, color: Colors.blueGrey),
                                                const SizedBox(width: 8),
                                                Expanded(
                                                  child: Text(msg,
                                                      style: Theme.of(context).textTheme.bodyMedium),
                                                ),
                                              ],
                                            ),
                                          ),

                                        const SizedBox(height: 8),
                                        Text(
                                          '*Thời gian ước tính sơ bộ theo vận tốc trung bình 30 km/h.',
                                          style: Theme.of(context).textTheme.bodySmall,
                                        ),
                                      ],
                                    ),
                                  ),
                                ),

                                const SizedBox(height: 8),

                                // Disclaimer Card
                                Card(
                                  color: Theme.of(context)
                                      .colorScheme
                                      .surfaceContainerHighest
                                      .withValues(alpha: 0.5),
                                  child: Padding(
                                    padding: const EdgeInsets.all(12),
                                    child: Row(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const Icon(Icons.gavel, size: 18, color: Colors.grey),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            res.disclaimer,
                                            style: Theme.of(context).textTheme.bodySmall,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),

                                const SizedBox(height: 24),
                              ],
                            ],
                          ),
              ),
            ],
          );
        },
      ),
    );
  }
}
