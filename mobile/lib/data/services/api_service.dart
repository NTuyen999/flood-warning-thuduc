import '../models/forecast.dart';
import '../models/road_segment.dart';

abstract class ApiService {
  Future<List<RoadSegment>> getRoadSegments();
  Future<Forecast> getForecast(String segmentId);
}