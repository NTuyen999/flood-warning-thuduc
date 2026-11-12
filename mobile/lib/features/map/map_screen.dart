import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';

import '../../core/risk_colors.dart';
import '../../core/widgets.dart';
import '../../data/models/report.dart';
import '../../data/models/road_segment.dart';
import '../report/history_screen.dart';

final _hm = DateFormat('HH:mm');

/// Risk map tab: coloured road segments, community report markers, hour picker.
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

  @override
  void dispose() {
    _hit.dispose();
    _controller.dispose();
    super.dispose();
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

  void _showSegment(RoadSegment s) => showModalBottomSheet<void>(
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
                    Expanded(
                      child: FilledButton.tonalIcon(
                        onPressed: () => go(widget.onReport),
                        icon: const Icon(Icons.add_location_alt),
                        label: const Text('Báo cáo'),
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
            child: ReportCard(r, place: widget.map.segmentName(r.segmentId)),
          ),
        ),
      );

  String _horizonText() => widget.horizon == null
      ? 'trong 6 giờ tới'
      : 'lúc ${_hm.format(widget.map.issuedAt.add(Duration(hours: widget.horizon!)))}';

  @override
  Widget build(BuildContext context) {
    final map = widget.map;
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
              if (seg != null) _showSegment(seg);
            },
            child: PolylineLayer<String>(
              hitNotifier: _hit,
              minimumHitbox: 24, // finger-sized, the lines are only 7 px wide
              polylines: [
                for (final s in map.segments)
                  Polyline<String>(
                    points: s.points,
                    strokeWidth: 7,
                    color: riskColor(s.level),
                    borderStrokeWidth: 2,
                    borderColor: Colors.white,
                    hitValue: s.id,
                  ),
              ],
            ),
          ),
          MarkerLayer(markers: [
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
      // Status banner + hour picker
      Positioned(
        top: 8,
        left: 12,
        right: 12,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Card(
            child: ListTile(
              leading: Icon(riskIcon(map.worstLevel), color: riskColor(map.worstLevel), size: 36),
              title: Text('Nguy cơ mưa lớn: ${riskLabel(map.worstLevel)}'),
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
                    onSelected: (_) => widget.onHorizon(h),
                  ),
                ),
            ]),
          ),
        ]),
      ),
      Positioned(left: 12, bottom: 28, child: _Legend(map.legend)),
      Positioned(
        right: 16,
        bottom: 88,
        child: FloatingActionButton.small(
          heroTag: 'me',
          tooltip: 'Vị trí của tôi',
          onPressed: _goToMe,
          child: const Icon(Icons.my_location),
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
