class HorizonRisk {
  final int h;
  final double probability;
  final String level;

  HorizonRisk(this.h, this.probability, this.level);

  factory HorizonRisk.fromJson(Map<String, dynamic> j) => HorizonRisk(
    j['h'] as int,
    (j['probability'] as num).toDouble(),
    j['level'] as String,
  );
}

class Forecast {
  final String segmentId;
  final DateTime issuedAt;
  final bool isMock;
  final List<HorizonRisk> horizons;

  Forecast(this.segmentId, this.issuedAt, this.isMock, this.horizons);

  factory Forecast.fromJson(Map<String, dynamic> j) => Forecast(
    j['segment_id'] as String,
    DateTime.parse(j['issued_at'] as String),
    (j['is_mock'] as bool?) ?? false,
    (j['horizons'] as List)
        .map((e) => HorizonRisk.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}