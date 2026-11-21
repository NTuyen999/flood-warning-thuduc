import 'package:latlong2/latlong.dart';

class DemoScenario {
  final String id;
  final String label;
  final String description;
  final double rainMmPerH;
  final String banner;

  DemoScenario({
    required this.id,
    required this.label,
    required this.description,
    required this.rainMmPerH,
    required this.banner,
  });

  factory DemoScenario.fromJson(Map<String, dynamic> j) => DemoScenario(
        id: j['id'] as String,
        label: j['label'] as String,
        description: j['description'] as String,
        rainMmPerH: (j['rain_mm_per_h'] as num).toDouble(),
        banner: j['banner'] as String,
      );
}

class RoutePoint {
  final String id;
  final String nodeId;
  final String name;
  final LatLng coordinates;

  RoutePoint({
    required this.id,
    required this.nodeId,
    required this.name,
    required this.coordinates,
  });

  factory RoutePoint.fromJson(Map<String, dynamic> j) {
    final c = j['coordinates'] as List;
    return RoutePoint(
      id: j['id'] as String,
      nodeId: j['node_id'] as String,
      name: j['name'] as String,
      coordinates: LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble()),
    );
  }
}

class RoutePath {
  final double lengthM;
  final double etaMin;
  final String maxLevel;
  final List<String> edges;
  final List<String> blockedEdges;
  final List<LatLng> geometry;

  RoutePath({
    required this.lengthM,
    required this.etaMin,
    required this.maxLevel,
    required this.edges,
    required this.blockedEdges,
    required this.geometry,
  });

  factory RoutePath.fromJson(Map<String, dynamic> j) {
    final geom = j['geometry'];
    final coords = (geom != null && geom['coordinates'] != null)
        ? [
            for (final c in geom['coordinates'] as List)
              LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble())
          ]
        : <LatLng>[];

    return RoutePath(
      lengthM: (j['length_m'] as num).toDouble(),
      etaMin: (j['eta_min'] as num).toDouble(),
      maxLevel: (j['max_level'] as String?) ?? 'green',
      edges: [for (final e in (j['edges'] as List? ?? [])) e as String],
      blockedEdges: [for (final e in (j['blocked_edges'] as List? ?? [])) e as String],
      geometry: coords,
    );
  }
}

class RouteResult {
  final String status;
  final String scenario;
  final String fromPoint;
  final String toPoint;
  final int? horizon;
  final RoutePath? recommended;
  final RoutePath? shortest;
  final List<String> messages;
  final String disclaimer;
  final bool isDemo;

  RouteResult({
    required this.status,
    required this.scenario,
    required this.fromPoint,
    required this.toPoint,
    this.horizon,
    this.recommended,
    this.shortest,
    required this.messages,
    required this.disclaimer,
    required this.isDemo,
  });

  factory RouteResult.fromJson(Map<String, dynamic> j) => RouteResult(
        status: j['status'] as String,
        scenario: j['scenario'] as String,
        fromPoint: j['from_point'] as String,
        toPoint: j['to_point'] as String,
        horizon: j['horizon'] as int?,
        recommended: j['recommended'] != null
            ? RoutePath.fromJson(j['recommended'] as Map<String, dynamic>)
            : null,
        shortest: j['shortest'] != null
            ? RoutePath.fromJson(j['shortest'] as Map<String, dynamic>)
            : null,
        messages: [for (final m in (j['messages'] as List? ?? [])) m as String],
        disclaimer: (j['disclaimer'] as String?) ?? '',
        isDemo: (j['is_demo'] as bool?) ?? true,
      );
}
