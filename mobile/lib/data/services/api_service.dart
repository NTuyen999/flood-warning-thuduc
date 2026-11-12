import 'package:dio/dio.dart';
import 'package:latlong2/latlong.dart';

import '../models/forecast.dart';
import '../models/report.dart';
import '../models/road_segment.dart';

/// Backend address. Default = host machine seen from the Android emulator.
/// Real phone: flutter run --dart-define=API_URL=http://192.168.1.10:8000
const apiBaseUrl = String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000');

class ApiException implements Exception {
  final String message;
  final int? status;

  ApiException(this.message, [this.status]);

  @override
  String toString() => message;
}

/// Client of the backend REST API (see backend/docs/architecture.md).
class ApiService {
  final Dio _dio;

  ApiService([Dio? dio])
      : _dio = dio ??
            Dio(BaseOptions(
              baseUrl: apiBaseUrl,
              connectTimeout: const Duration(seconds: 8),
              receiveTimeout: const Duration(seconds: 20),
            ));

  Future<T> _call<T>(Future<Response<dynamic>> Function() request, T Function(dynamic) parse) async {
    try {
      return parse((await request()).data);
    } on DioException catch (e) {
      throw ApiException(_message(e), e.response?.statusCode);
    }
  }

  /// The backend answers errors as {"detail": text | {"message": text} | [{"msg": text}]}.
  static String _message(DioException e) {
    final data = e.response?.data;
    final detail = data is Map ? data['detail'] : null;
    if (detail is String) return detail;
    if (detail is Map && detail['message'] is String) return detail['message'] as String;
    if (detail is List && detail.isNotEmpty) {
      return '${detail.first['msg']}'.replaceFirst('Value error, ', '');
    }
    if (e.response == null) return 'Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.';
    return 'Máy chủ đang lỗi (${e.response!.statusCode}). Thử lại sau.';
  }

  Future<RiskMap> getRiskMap({int? horizon}) => _call(
      () => _dio.get('/api/v1/map/risks',
          queryParameters: {'horizon': ?horizon}),
      (d) => RiskMap.fromJson(d as Map<String, dynamic>));

  Future<Forecast> getForecast(String segmentId) => _call(
      () => _dio.get('/api/v1/forecast/$segmentId'),
      (d) => Forecast.fromJson(d as Map<String, dynamic>));

  Future<Explanation> getExplanation(String segmentId, int horizon) => _call(
      () => _dio.get('/api/v1/explain/$segmentId', queryParameters: {'horizon': horizon}),
      (d) => Explanation.fromJson(d as Map<String, dynamic>));

  Future<Weather> getWeather() => _call(() => _dio.get('/api/v1/weather/current'),
      (d) => Weather.fromJson(d as Map<String, dynamic>));

  Future<List<Report>> getReports({String? segmentId}) => _call(
      () => _dio.get('/api/v1/reports',
          queryParameters: {'limit': 100, 'segment_id': ?segmentId}),
      (d) => [for (final r in d['items'] as List) Report.fromJson(r as Map<String, dynamic>)]);

  /// Uploads the photo first (if any), then sends the report. The server assigns the
  /// nearest road segment from the coordinates.
  Future<Report> sendReport({
    required LatLng at,
    required String floodLevel,
    String? note,
    String? imagePath,
  }) =>
      _call(() async {
        String? imageUrl;
        if (imagePath != null) {
          final upload = await _dio.post('/api/v1/uploads',
              data: FormData.fromMap({'file': await MultipartFile.fromFile(imagePath)}));
          imageUrl = upload.data['image_url'] as String;
        }
        return _dio.post('/api/v1/reports', data: {
          'lat': at.latitude,
          'lon': at.longitude,
          'flood_level': floodLevel,
          if (note != null && note.isNotEmpty) 'note': note,
          'image_url': ?imageUrl,
        });
      }, (d) => Report.fromJson(d as Map<String, dynamic>));

  /// Absolute URL of a report photo ("/uploads/x.jpg" in the API).
  String imageUrl(String path) => '${_dio.options.baseUrl}$path';
}
