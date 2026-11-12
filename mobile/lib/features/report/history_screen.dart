import 'package:flutter/material.dart';

import '../../core/risk_colors.dart';
import '../../core/widgets.dart';
import '../../data/models/report.dart';
import '../../data/services/api.dart';

/// One community report: photo or flood icon, level, place, age, status.
class ReportCard extends StatelessWidget {
  final Report report;
  final String? place;

  const ReportCard(this.report, {super.key, this.place});

  @override
  Widget build(BuildContext context) {
    final color = floodColor(report.floodLevel);
    final avatar = CircleAvatar(
      radius: 26,
      backgroundColor: color.withValues(alpha: 0.16),
      child: Icon(floodIcon(report.floodLevel), color: color),
    );
    final (statusIcon, statusColor) = switch (report.status) {
      'new' => (Icons.schedule, const Color(0xFFE5A800)),
      'verified' => (Icons.verified, const Color(0xFF2E9E5B)),
      'expired' => (Icons.history, Colors.blueGrey),
      _ => (Icons.block, const Color(0xFFD93025)),
    };
    final url = report.imageUrl == null ? null : api.imageUrl(report.imageUrl!);
    return Opacity(
      opacity: report.active ? 1 : 0.6,
      child: Card(
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          leading: url == null
              ? avatar
              : GestureDetector(
                  onTap: () => showDialog<void>(
                    context: context,
                    builder: (_) => Dialog(
                      clipBehavior: Clip.antiAlias,
                      child: InteractiveViewer(child: Image.network(url)),
                    ),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.network(url, width: 52, height: 52, fit: BoxFit.cover,
                        errorBuilder: (_, _, _) => avatar),
                  ),
                ),
          title: Text(floodLabel(report.floodLevel)),
          subtitle: Text([
            '${place ?? 'Ngoài các đoạn theo dõi'} · ${ago(report.ageMinutes)}',
            if (report.note != null) report.note!,
          ].join('\n')),
          trailing: Pill(statusIcon, statusLabel(report.status), statusColor),
        ),
      ),
    );
  }
}

/// Report list with an "active only / all" switch, pull-to-refresh and an empty state.
class ReportList extends StatefulWidget {
  final List<Report> reports;
  final String? Function(String? segmentId) placeOf;
  final Future<void> Function() onRefresh;

  const ReportList(
      {super.key, required this.reports, required this.placeOf, required this.onRefresh});

  @override
  State<ReportList> createState() => _ReportListState();
}

class _ReportListState extends State<ReportList> {
  bool _activeOnly = true;

  @override
  Widget build(BuildContext context) {
    final shown = widget.reports.where((r) => !_activeOnly || r.active).toList();
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: SegmentedButton<bool>(
          segments: const [
            ButtonSegment(value: true, label: Text('Còn hiệu lực')),
            ButtonSegment(value: false, label: Text('Tất cả')),
          ],
          selected: {_activeOnly},
          onSelectionChanged: (s) => setState(() => _activeOnly = s.first),
        ),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: widget.onRefresh,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 96),
            children: shown.isEmpty
                ? const [
                    EmptyState(Icons.forum_outlined,
                        'Chưa có báo cáo nào.\nThấy đường ngập hay khô ráo? Bấm "Báo cáo" để giúp mọi người.'),
                  ]
                : [for (final r in shown) ReportCard(r, place: widget.placeOf(r.segmentId))],
          ),
        ),
      ),
    ]);
  }
}
