import 'package:latlong2/latlong.dart';

class RoadSegment {
  final String id;
  final String name;
  final List<LatLng> points;

  RoadSegment(this.id, this.name, this.points);
}