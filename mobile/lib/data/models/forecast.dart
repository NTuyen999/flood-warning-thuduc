import '../../core/risk_colors.dart';

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

/// GET /api/v1/forecast/{segment_id}
class Forecast {
  final String segmentId;
  final DateTime issuedAt;
  final bool stale;
  final String disclaimer;
  final List<HorizonRisk> horizons;

  Forecast(this.segmentId, this.issuedAt, this.stale, this.disclaimer, this.horizons);

  /// Highest-risk hour; the earliest one when several share the level.
  HorizonRisk? get worst => horizons.fold<HorizonRisk?>(
      null,
      (a, b) => a == null || riskOrder.indexOf(b.level) > riskOrder.indexOf(a.level) ? b : a);

  DateTime timeOf(int h) => issuedAt.add(Duration(hours: h));

  factory Forecast.fromJson(Map<String, dynamic> j) => Forecast(
    j['segment_id'] as String,
    DateTime.parse(j['issued_at'] as String).toLocal(),
    (j['stale'] as bool?) ?? false,
    (j['disclaimer'] as String?) ?? '',
    (j['horizons'] as List)
        .map((e) => HorizonRisk.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}

class ExplainFeature {
  final String label;
  final String text;
  final double impact;

  ExplainFeature(this.label, this.text, this.impact);
}

/// GET /api/v1/explain/{segment_id}?horizon=
class Explanation {
  final double probability;
  final String level;
  final String note;
  final List<ExplainFeature> features;

  Explanation(this.probability, this.level, this.note, this.features);

  factory Explanation.fromJson(Map<String, dynamic> j) => Explanation(
    (j['probability'] as num).toDouble(),
    j['level'] as String,
    (j['note'] as String?) ?? '',
    [
      for (final f in j['features'] as List)
        ExplainFeature(f['label'] as String, f['text'] as String,
            (f['impact'] as num).toDouble()),
    ],
  );
}

/// GET /api/v1/weather/current
class Weather {
  final DateTime observedAt;
  final double temperature;
  final double humidity;
  final double precipitation;
  final double windSpeed;

  Weather(this.observedAt, this.temperature, this.humidity, this.precipitation, this.windSpeed);

  factory Weather.fromJson(Map<String, dynamic> j) => Weather(
    DateTime.parse(j['observed_at'] as String).toLocal(),
    (j['temperature_2m'] as num).toDouble(),
    (j['relative_humidity_2m'] as num).toDouble(),
    (j['precipitation'] as num).toDouble(),
    (j['wind_speed_10m'] as num).toDouble(),
  );
}
