import 'package:flutter/material.dart';

import '../../core/risk_colors.dart';
import '../../data/models/road_segment.dart';

/// Road list tab: the same data as the map, searchable by name. Roads with
/// flood reports come first.
class SegmentsTab extends StatefulWidget {
  final RiskMap map;
  final void Function(RoadSegment) onTap;

  const SegmentsTab({super.key, required this.map, required this.onTap});

  @override
  State<SegmentsTab> createState() => _SegmentsTabState();
}

class _SegmentsTabState extends State<SegmentsTab> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final shown = widget.map.segments
        .where((s) => s.name.toLowerCase().contains(_query.toLowerCase()))
        .toList()
      ..sort((a, b) => b.floodedReports.compareTo(a.floodedReports));
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
        child: SearchBar(
          hintText: 'Tìm tên đường',
          leading: const Icon(Icons.search),
          elevation: const WidgetStatePropertyAll(0),
          onChanged: (q) => setState(() => _query = q.trim()),
        ),
      ),
      Expanded(
        child: shown.isEmpty
            ? const Center(child: Text('Không có đường nào khớp.'))
            : ListView.builder(
                itemCount: shown.length,
                itemBuilder: (context, i) {
                  final s = shown[i];
                  final color = riskColor(s.level);
                  return ListTile(
                    leading: CircleAvatar(
                      backgroundColor: color.withValues(alpha: 0.16),
                      child: Icon(riskIcon(s.level), color: color),
                    ),
                    title: Text(s.name),
                    subtitle: Text([
                      'Nguy cơ ${riskLabel(s.level).toLowerCase()}',
                      if (s.probability != null) percent(s.probability!),
                      if (s.floodedReports > 0) '${s.floodedReports} báo cáo ngập',
                    ].join(' · ')),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => widget.onTap(s),
                  );
                },
              ),
      ),
    ]);
  }
}
