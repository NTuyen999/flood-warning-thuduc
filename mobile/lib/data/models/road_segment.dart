import 'package:latlong2/latlong.dart';

import '../../core/risk_colors.dart';

/// One feature of GET /api/v1/map/risks.
class RoadSegment {
  final String id;
  final String name;
  final List<LatLng> points;
  final double? probability;
  final String? level;
  final int activeReports;
  final int floodedReports;

  RoadSegment(this.id, this.name, this.points, this.probability, this.level,
      this.activeReports, this.floodedReports);

  LatLng get middle => points[points.length ~/ 2];

  factory RoadSegment.fromFeature(Map<String, dynamic> f) {
    final p = f['properties'] as Map<String, dynamic>;
    final reports = (p['report_summary'] as Map<String, dynamic>?) ?? const {};
    return RoadSegment(
      p['segment_id'] as String,
      p['name'] as String,
      // GeoJSON is [lon, lat]
      [
        for (final c in f['geometry']['coordinates'] as List)
          LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble()),
      ],
      (p['probability'] as num?)?.toDouble(),
      p['risk_level'] as String?,
      (reports['active'] as int?) ?? 0,
      (reports['flooded'] as int?) ?? 0,
    );
  }
}

class LegendItem {
  final String level;
  final String label;
  final double maxProbability;

  LegendItem(this.level, this.label, this.maxProbability);
}

class RiskMap {
  final DateTime issuedAt;
  final bool stale;
  final String disclaimer;
  final List<LegendItem> legend;
  final List<RoadSegment> segments;

  RiskMap(this.issuedAt, this.stale, this.disclaimer, this.legend, this.segments);

  String? get worstLevel => segments
      .map((s) => s.level)
      .fold<String?>(null, (a, b) => riskOrder.indexOf(b ?? '') > riskOrder.indexOf(a ?? '') ? b : a);

  String? segmentName(String? id) =>
      segments.where((s) => s.id == id).map((s) => s.name).firstOrNull;

  factory RiskMap.fromJson(Map<String, dynamic> j) => RiskMap(
    DateTime.parse(j['issued_at'] as String).toLocal(),
    (j['stale'] as bool?) ?? false,
    (j['disclaimer'] as String?) ?? '',
    [
      for (final l in j['legend'] as List)
        LegendItem(l['level'] as String, l['label'] as String,
            (l['max_probability'] as num).toDouble()),
    ],
    [for (final f in j['features'] as List) RoadSegment.fromFeature(f as Map<String, dynamic>)],
  );
}
