import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:latlong2/latlong.dart';
import '../models/forecast.dart';
import '../models/road_segment.dart';
import 'api_service.dart';

class MockApiService implements ApiService {
  @override
  Future<List<RoadSegment>> getRoadSegments() async {
    final raw =
    await rootBundle.loadString('assets/mock/road_segments.geojson');
    final features = jsonDecode(raw)['features'] as List;
    return features.map((f) {
      final coords = f['geometry']['coordinates'] as List;
      return RoadSegment(
        f['properties']['segment_id'] as String,
        f['properties']['name'] as String,
        // GeoJSON là [lng, lat] nên phải đảo thành LatLng(lat, lng)
        coords.map((c) => LatLng(c[1] as double, c[0] as double)).toList(),
      );
    }).toList();
  }

  @override
  Future<Forecast> getForecast(String segmentId) async {
    final raw =
    await rootBundle.loadString('assets/mock/forecast_TD01.json');
    final j = jsonDecode(raw) as Map<String, dynamic>;
    j['segment_id'] = segmentId; // dùng chung 1 file mock cho mọi đoạn
    return Forecast.fromJson(j);
  }
}