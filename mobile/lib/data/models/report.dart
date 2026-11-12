import 'package:latlong2/latlong.dart';

/// One item of GET /api/v1/reports.
class Report {
  final int id;
  final String? segmentId;
  final LatLng location;
  final String floodLevel;
  final String status;
  final int ageMinutes;
  final String? note;
  final String? imageUrl;

  Report(this.id, this.segmentId, this.location, this.floodLevel, this.status,
      this.ageMinutes, this.note, this.imageUrl);

  bool get active => status == 'new' || status == 'verified';

  factory Report.fromJson(Map<String, dynamic> j) => Report(
    j['id'] as int,
    j['segment_id'] as String?,
    LatLng((j['lat'] as num).toDouble(), (j['lon'] as num).toDouble()),
    j['flood_level'] as String,
    j['status'] as String,
    (j['age_minutes'] as int?) ?? 0,
    j['note'] as String?,
    j['image_url'] as String?,
  );
}
