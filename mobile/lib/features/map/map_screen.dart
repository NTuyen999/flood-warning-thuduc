import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';

import '../../core/demo_mode.dart';
import '../../core/risk_colors.dart';
import '../../core/widgets.dart';
import '../../data/models/report.dart';
import '../../data/models/road_segment.dart';
import '../../data/services/api.dart';
import '../report/history_screen.dart';
import '../route/route_screen.dart';

final _hm = DateFormat('HH:mm');

/// Risk map tab: coloured road segments, community report markers, hour picker, simulation mode.
class MapTab extends StatefulWidget {
  final RiskMap map;
  final List<Report> reports;
  final int? horizon;
  final ValueChanged<int?> onHorizon;
  final void Function(RoadSegment) onForecast;
  final void Function(RoadSegment) onReport;

  const MapTab({
    super.key,
    required this.map,
    required this.reports,
    required this.horizon,
    required this.onHorizon,
    required this.onForecast,
    required this.onReport,
  });

  @override
  State<MapTab> createState() => _MapTabState();
}

class _MapTabState extends State<MapTab> {
  final LayerHitNotifier<String> _hit = ValueNotifier(null);
  final _controller = MapController();
  LatLng? _me;
  RiskMap? _demoMap;

  @override
  void initState() {
    super.initState();
    demoMode.addListener(_onDemoModeChanged);
    if (demoMode.value.enabled) _loadDemoMap();
  }

  @override
  void dispose() {
    demoMode.removeListener(_onDemoModeChanged);
    _hit.dispose();
    _controller.dispose();
    super.dispose();
  }

  void _onDemoModeChanged() {
    if (demoMode.value.enabled) {
      _loadDemoMap();
    } else {
      if (mounted) setState(() => _demoMap = null);
    }
  }

  Future<void> _loadDemoMap() async {
    try {
      final map = await api.getDemoMap(
        scenario: demoMode.value.scenario,
        horizon: widget.horizon,
      );
      if (!mounted) return;
      setState(() {
        _demoMap = map;
      });
    } catch (_) {}
  }

  Future<void> _goToMe() async {
    final here = await currentLocation();
    if (!mounted) return;
    if (here == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Không lấy được vị trí. Hãy bật định vị và cấp quyền cho ứng dụng.')));
      return;
    }
    setState(() => _me = here);
    _controller.move(here, 15);
  }

  void _openRouteScreen() {
    if (!demoMode.value.enabled) {
      showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          icon: const Icon(Icons.science, size: 36, color: Colors.amber),
          title: const Text('Gợi ý đường đi'),
          content: const Text(
            'Tính năng gợi ý đường đi hiện chạy trên khu vực mạng mô phỏng thu nhỏ TP Thủ Đức.\n\n'
            'Bật chế độ mô phỏng để trải nghiệm tính năng này?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Hủy'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext);
                demoMode.setEnabled(true);
                Navigator.push(
                  context,
                  MaterialPageRoute<void>(builder: (_) => const RouteScreen()),
                );
              },
              child: const Text('Bật chế độ mô phỏng'),
            ),
          ],
        ),
      );
    } else {
      Navigator.push(
        context,
        MaterialPageRoute<void>(builder: (_) => const RouteScreen()),
      );
    }
  }

  void showSegment(RoadSegment s) => showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        builder: (sheet) {
          final text = Theme.of(sheet).textTheme;
          void go(void Function(RoadSegment) action) {
            Navigator.pop(sheet);
            action(s);
          }

          return SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Expanded(child: Text(s.name, style: text.titleLarge)),
                    Pill.risk(s.level),
                  ]),
                  const SizedBox(height: 8),

                  // Alley & simulation tags
                  if (s.kind == 'alley') ...[
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        if (s.deadEnd)
                          Pill(Icons.do_not_disturb_on, 'Hẻm cụt', Colors.purple),
                        Pill(
                          Icons.alt_route,
                          s.levelSource.startsWith('inherited:')
                              ? 'Ngập tràn từ đường chính ${s.parentSegmentId}'
                              : 'Hẻm tự ngập',
                          Colors.blueGrey,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                  ],

                  if (s.blocked)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: Colors.red.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.red),
                        ),
                        child: const Row(
                          children: [
                            Icon(Icons.block, color: Colors.red, size: 18),
                            SizedBox(width: 8),
                            Text('KHÔNG VÀO ĐƯỢC (ĐOẠN BỊ CHẶN)',
                                style: TextStyle(
                                    color: Colors.red,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12)),
                          ],
                        ),
                      ),
                    ),

                  Text(riskSentence(s.level)),
                  if (s.probability != null)
                    Text('Khả năng mưa lớn ${_horizonText()}: ${percent(s.probability!)}',
                        style: text.bodySmall),

                  if (s.activeReports > 0) ...[
                    const SizedBox(height: 8),
                    Pill(
                      Icons.groups,
                      '${s.activeReports} báo cáo còn hiệu lực, ${s.floodedReports} báo ngập',
                      floodColor(s.floodedReports > 0 ? 'heavy' : 'none'),
                    ),
                  ],
                  const SizedBox(height: 16),
                  Row(children: [
                    if (!s.isDemo)
                      Expanded(
                        child: FilledButton.tonalIcon(
                          onPressed: () => go(widget.onReport),
                          icon: const Icon(Icons.add_location_alt),
                          label: const Text('Báo cáo'),
                        ),
                      )
                    else
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () {
                            Navigator.pop(sheet);
                            _openRouteScreen();
                          },
                          icon: const Icon(Icons.navigation),
                          label: const Text('Chỉ đường'),
                        ),
                      ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: () => go(widget.onForecast),
                        icon: const Icon(Icons.bar_chart),
                        label: const Text('Xem dự báo'),
                      ),
                    ),
                  ]),
                ],
              ),
            ),
          );
        },
      );

  void _showReport(Report r) => showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        builder: (_) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 20),
            child: ReportCard(r, place: (demoMode.value.enabled ? _demoMap : widget.map)?.segmentName(r.segmentId)),
          ),
        ),
      );

  String _horizonText() {
    final map = demoMode.value.enabled ? (_demoMap ?? widget.map) : widget.map;
    return widget.horizon == null
        ? 'trong 6 giờ tới'
        : 'lúc ${_hm.format(map.issuedAt.add(Duration(hours: widget.horizon!)))}';
  }

  @override
  Widget build(BuildContext context) {
    final isDemo = demoMode.value.enabled;
    final map = isDemo ? (_demoMap ?? widget.map) : widget.map;
    final scheme = Theme.of(context).colorScheme;

    return Stack(children: [
      BaseMap(
        controller: _controller,
        options: MapOptions(
          initialCameraFit: CameraFit.coordinates(
            coordinates: [for (final s in map.segments) ...s.points],
            padding: const EdgeInsets.fromLTRB(40, 150, 40, 110),
          ),
          interactionOptions:
              const InteractionOptions(flags: InteractiveFlag.all & ~InteractiveFlag.rotate),
        ),
        children: [
          GestureDetector(
            onTap: () {
              final id = _hit.value?.hitValues.firstOrNull;
              final seg = map.segments.where((s) => s.id == id).firstOrNull;
              if (seg != null) showSegment(seg);
            },
            child: PolylineLayer<String>(
              hitNotifier: _hit,
              minimumHitbox: 24,
              polylines: [
                for (final s in map.segments)
                  Polyline<String>(
                    points: s.points,
                    strokeWidth: s.kind == 'alley' ? 5 : 7,
                    pattern: s.kind == 'alley'
                        ? StrokePattern.dashed(segments: [10.0, 6.0])
                        : const StrokePattern.solid(),
                    color: riskColor(s.level),
                    borderStrokeWidth: s.blocked ? 3.5 : 2,
                    borderColor: s.blocked ? Colors.red.shade900 : Colors.white,
                    hitValue: s.id,
                  ),
              ],
            ),
          ),
          MarkerLayer(markers: [
            // Dead end icons for alley endpoints
            for (final s in map.segments)
              if (s.deadEnd && s.points.isNotEmpty)
                Marker(
                  point: s.points.last,
                  width: 28,
                  height: 28,
                  child: Semantics(
                    label: 'Hẻm cụt: ${s.name}',
                    child: DecoratedBox(
                      decoration: const BoxDecoration(
                        color: Colors.white,
                        shape: BoxShape.circle,
                        boxShadow: [BoxShadow(blurRadius: 3, color: Colors.black26)],
                      ),
                      child: Icon(
                        Icons.do_not_disturb_on,
                        size: 20,
                        color: riskColor(s.level),
                      ),
                    ),
                  ),
                ),

            // Community reports markers
            for (final r in widget.reports.where((r) => r.active))
              Marker(
                point: r.location,
                width: 40,
                height: 40,
                child: Semantics(
                  button: true,
                  label: 'Báo cáo: ${floodLabel(r.floodLevel)}, ${ago(r.ageMinutes)}',
                  child: GestureDetector(
                    onTap: () => _showReport(r),
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        shape: BoxShape.circle,
                        border: Border.all(color: floodColor(r.floodLevel), width: 2.5),
                        boxShadow: const [BoxShadow(blurRadius: 4, color: Colors.black26)],
                      ),
                      child: Icon(floodIcon(r.floodLevel),
                          color: floodColor(r.floodLevel), size: 22),
                    ),
                  ),
                ),
              ),

            if (_me != null)
              Marker(
                point: _me!,
                width: 22,
                height: 22,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: scheme.primary,
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 3),
                    boxShadow: const [BoxShadow(blurRadius: 4, color: Colors.black38)],
                  ),
                ),
              ),
          ]),
        ],
      ),

      // Status banner + hour picker + simulation controls
      Positioned(
        top: 8,
        left: 12,
        right: 12,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (isDemo) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.tertiaryContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(children: [
                Icon(Icons.science,
                    color: Theme.of(context).colorScheme.onTertiaryContainer, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'ĐANG XEM DỮ LIỆU MÔ PHỎNG – không phải dự báo thật',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onTertiaryContainer,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ]),
            ),
            SingleChildScrollView(
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
                        selected: demoMode.value.scenario == sc.$1,
                        onSelected: (_) {
                          demoMode.setScenario(sc.$1);
                          _loadDemoMap();
                        },
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 4),
          ] else if (map.stale)
            Container(
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(children: [
                Icon(Icons.warning_amber_rounded,
                    color: Theme.of(context).colorScheme.onErrorContainer, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Dữ liệu cũ (nguồn thời tiết chậm cập nhật)',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onErrorContainer,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ]),
            ),

          Card(
            child: ListTile(
              leading: Icon(riskIcon(map.worstLevel), color: riskColor(map.worstLevel), size: 36),
              title: Text(isDemo
                  ? 'Kịch bản mô phỏng: ${riskLabel(map.worstLevel)}'
                  : 'Nguy cơ mưa lớn: ${riskLabel(map.worstLevel)}'),
              subtitle: Text(map.stale
                  ? 'Dữ liệu cũ từ ${_hm.format(map.issuedAt)}: nguồn thời tiết đang lỗi'
                  : 'Cập nhật ${_hm.format(map.issuedAt)} · ${_horizonText()}'),
            ),
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              for (final h in [null, 1, 2, 3, 4, 5, 6])
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: ChoiceChip(
                    label: Text(h == null
                        ? 'Cả 6 giờ'
                        : _hm.format(map.issuedAt.add(Duration(hours: h)))),
                    selected: widget.horizon == h,
                    onSelected: (_) {
                      widget.onHorizon(h);
                      if (isDemo) _loadDemoMap();
                    },
                  ),
                ),
            ]),
          ),
        ]),
      ),

      Positioned(left: 12, bottom: 28, child: _Legend(map.legend)),

      // Floating Action Buttons (Route & My Location)
      Positioned(
        right: 16,
        bottom: 88,
        child: Column(
          children: [
            FloatingActionButton.small(
              heroTag: 'route',
              tooltip: 'Gợi ý đường đi',
              onPressed: _openRouteScreen,
              child: const Icon(Icons.navigation),
            ),
            const SizedBox(height: 8),
            FloatingActionButton.small(
              heroTag: 'me',
              tooltip: 'Vị trí của tôi',
              onPressed: _goToMe,
              child: const Icon(Icons.my_location),
            ),
          ],
        ),
      ),
    ]);
  }
}

class _Legend extends StatelessWidget {
  final List<LegendItem> items;

  const _Legend(this.items);

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    var lower = 0.0;
    final rows = <Widget>[];
    for (final item in items) {
      final range = lower == 0
          ? '<${percent(item.maxProbability)}'
          : item.maxProbability >= 1
              ? '≥${percent(lower)}'
              : '${(lower * 100).round()}–${percent(item.maxProbability)}';
      rows.add(Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(riskIcon(item.level), size: 14, color: riskColor(item.level)),
        const SizedBox(width: 4),
        Text('${item.label} ', style: text.labelMedium),
        Text(range, style: text.bodySmall),
      ]));
      lower = item.maxProbability;
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Khả năng mưa lớn', style: text.labelSmall),
          ...rows,
        ]),
      ),
    );
  }
}
