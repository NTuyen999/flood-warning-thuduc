import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/risk_colors.dart';
import 'package:mobile/data/models/forecast.dart';
import 'package:mobile/data/models/report.dart';
import 'package:mobile/data/models/road_segment.dart';
import 'package:mobile/data/services/api_service.dart';

class _MockAdapter implements HttpClientAdapter {
  final Future<ResponseBody> Function(RequestOptions) handler;
  _MockAdapter(this.handler);

  @override
  Future<ResponseBody> fetch(
      RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) {
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  group('Forecast model', () {
    test('Forecast.fromJson parses valid JSON', () {
      final json = {
        'segment_id': 'SEG01',
        'issued_at': '2026-11-12T09:00:00+07:00',
        'stale': false,
        'disclaimer': 'Test disclaimer',
        'horizons': [
          {'h': 1, 'probability': 0.05, 'level': 'green'},
          {'h': 2, 'probability': 0.35, 'level': 'orange'},
        ],
      };
      final f = Forecast.fromJson(json);
      expect(f.segmentId, 'SEG01');
      expect(f.stale, isFalse);
      expect(f.disclaimer, 'Test disclaimer');
      expect(f.horizons.length, 2);
      expect(f.horizons[1].level, 'orange');
    });

    test('Forecast.worst returns highest risk level and earliest hour on tie', () {
      final json = {
        'segment_id': 'SEG01',
        'issued_at': '2026-11-12T09:00:00+07:00',
        'stale': false,
        'disclaimer': '',
        'horizons': [
          {'h': 1, 'probability': 0.1, 'level': 'yellow'},
          {'h': 2, 'probability': 0.7, 'level': 'red'}, // Red at h=2
          {'h': 3, 'probability': 0.8, 'level': 'red'}, // Red at h=3 (tie in level)
          {'h': 4, 'probability': 0.4, 'level': 'orange'},
        ],
      };
      final f = Forecast.fromJson(json);
      expect(f.worst?.h, 2); // Earliest hour when tie
      expect(f.worst?.level, 'red');
    });
  });

  group('RiskMap and RoadSegment models', () {
    test('RiskMap.fromJson handles null probability and missing report_summary', () {
      final json = {
        'issued_at': '2026-11-12T09:00:00+07:00',
        'stale': true,
        'disclaimer': 'Bản đồ nguy cơ',
        'legend': [
          {'level': 'green', 'label': 'Thấp', 'max_probability': 0.1},
        ],
        'features': [
          {
            'type': 'Feature',
            'geometry': {
              'type': 'LineString',
              'coordinates': [
                [106.76, 10.85],
                [106.77, 10.86],
              ],
            },
            'properties': {
              'segment_id': 'SEG_NOPROB',
              'name': 'Đường chưa có dự báo',
              'probability': null,
              'risk_level': null,
            },
          },
        ],
      };
      final map = RiskMap.fromJson(json);
      expect(map.stale, isTrue);
      expect(map.segments.length, 1);
      final seg = map.segments.first;
      expect(seg.probability, isNull);
      expect(seg.level, isNull);
      expect(seg.activeReports, 0);
      expect(seg.floodedReports, 0);
      expect(map.worstLevel, isNull);
    });

    test('RiskMap.worstLevel returns the highest level across segments', () {
      final map = RiskMap(
        DateTime.now(),
        false,
        '',
        [],
        [
          RoadSegment('S1', 'Đường 1', [], 0.05, 'green', 0, 0),
          RoadSegment('S2', 'Đường 2', [], 0.65, 'red', 1, 1),
          RoadSegment('S3', 'Đường 3', [], 0.35, 'yellow', 0, 0),
        ],
      );
      expect(map.worstLevel, 'red');
    });
  });

  group('Explanation model', () {
    test('Explanation.fromJson parses SHAP features correctly', () {
      final json = {
        'probability': 0.66,
        'level': 'red',
        'note': 'Ghi chú SHAP',
        'features': [
          {
            'label': 'Tổng mưa 3h',
            'text': 'Tổng mưa 3 giờ = 15mm -> tăng nguy cơ',
            'impact': 1.8,
          },
        ],
      };
      final exp = Explanation.fromJson(json);
      expect(exp.probability, 0.66);
      expect(exp.level, 'red');
      expect(exp.note, 'Ghi chú SHAP');
      expect(exp.features.length, 1);
      expect(exp.features.first.impact, 1.8);
    });
  });

  group('Report model', () {
    test('Report.fromJson parses report and determines active status', () {
      final rNew = Report.fromJson({
        'id': 1,
        'segment_id': 'SEG01',
        'lat': 10.85,
        'lon': 106.77,
        'flood_level': 'light',
        'status': 'new',
        'age_minutes': 10,
        'note': 'Ngập nhẹ',
        'image_url': '/uploads/img1.jpg',
      });
      final rExp = Report.fromJson({
        'id': 2,
        'segment_id': null,
        'lat': 10.86,
        'lon': 106.78,
        'flood_level': 'heavy',
        'status': 'expired',
        'age_minutes': 400,
      });

      expect(rNew.active, isTrue);
      expect(rNew.imageUrl, '/uploads/img1.jpg');
      expect(rExp.active, isFalse);
      expect(rExp.segmentId, isNull);
    });
  });

  group('Weather model', () {
    test('Weather.fromJson parses Open-Meteo fields correctly', () {
      final json = {
        'observed_at': '2026-11-12T09:00:00+07:00',
        'temperature_2m': 28.5,
        'relative_humidity_2m': 85.0,
        'precipitation': 12.0,
        'wind_speed_10m': 15.2,
      };
      final w = Weather.fromJson(json);
      expect(w.temperature, 28.5);
      expect(w.humidity, 85.0);
      expect(w.precipitation, 12.0);
      expect(w.windSpeed, 15.2);
    });
  });

  group('ApiService error handling', () {
    final opts = RequestOptions(path: '/health');

    test('handles String detail', () async {
      final dio = Dio(BaseOptions(baseUrl: 'http://test'))
        ..httpClientAdapter = _MockAdapter((_) async {
          return ResponseBody.fromString(
            '{"detail": "Lỗi dữ liệu đầu vào"}',
            400,
            headers: {
              Headers.contentTypeHeader: [Headers.jsonContentType]
            },
          );
        });
      final service = ApiService(dio);
      expect(
        () => service.checkHealth(),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Lỗi dữ liệu đầu vào')),
      );
    });

    test('handles Map detail with message field', () async {
      final dio = Dio(BaseOptions(baseUrl: 'http://test'))
        ..httpClientAdapter = _MockAdapter((_) async {
          return ResponseBody.fromString(
            '{"detail": {"message": "Đã có người báo cáo trùng"}}',
            409,
            headers: {
              Headers.contentTypeHeader: [Headers.jsonContentType]
            },
          );
        });
      final service = ApiService(dio);
      expect(
        () => service.checkHealth(),
        throwsA(
            isA<ApiException>().having((e) => e.message, 'message', 'Đã có người báo cáo trùng')),
      );
    });

    test('handles List detail with Value error prefix removal', () async {
      final dio = Dio(BaseOptions(baseUrl: 'http://test'))
        ..httpClientAdapter = _MockAdapter((_) async {
          return ResponseBody.fromString(
            '{"detail": [{"msg": "Value error, Vị trí nằm ngoài TP Thủ Đức"}]}',
            422,
            headers: {
              Headers.contentTypeHeader: [Headers.jsonContentType]
            },
          );
        });
      final service = ApiService(dio);
      expect(
        () => service.checkHealth(),
        throwsA(isA<ApiException>()
            .having((e) => e.message, 'message', 'Vị trí nằm ngoài TP Thủ Đức')),
      );
    });

    test('handles network failure', () async {
      final dio = Dio(BaseOptions(baseUrl: 'http://test'))
        ..httpClientAdapter = _MockAdapter((_) async {
          throw DioException.connectionError(requestOptions: opts, reason: 'down');
        });
      final service = ApiService(dio);
      expect(
        () => service.checkHealth(),
        throwsA(isA<ApiException>().having((e) => e.message, 'message',
            'Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.')),
      );
    });

    test('handles generic 500 error', () async {
      final dio = Dio(BaseOptions(baseUrl: 'http://test'))
        ..httpClientAdapter = _MockAdapter((_) async {
          return ResponseBody.fromString(
            'Server Error',
            500,
            headers: {
              Headers.contentTypeHeader: [Headers.textPlainContentType]
            },
          );
        });
      final service = ApiService(dio);
      expect(
        () => service.checkHealth(),
        throwsA(isA<ApiException>()
            .having((e) => e.message, 'message', 'Máy chủ đang lỗi (500). Thử lại sau.')),
      );
    });
  });

  group('Helper functions (risk_colors)', () {
    test('percent formats probabilities correctly', () {
      expect(percent(0.004), '<1%');
      expect(percent(0.01), '1%');
      expect(percent(0.356), '36%');
      expect(percent(0.66), '66%');
    });

    test('ago formats minutes into readable Vietnamese relative time', () {
      expect(ago(0), 'Vừa xong');
      expect(ago(15), '15 phút trước');
      expect(ago(120), '2 giờ trước');
      expect(ago(2880), '2 ngày trước');
    });

    test('riskLabel returns Vietnamese labels', () {
      expect(riskLabel('green'), 'Thấp');
      expect(riskLabel('yellow'), 'Trung bình');
      expect(riskLabel('orange'), 'Cao');
      expect(riskLabel('red'), 'Rất cao');
      expect(riskLabel(null), 'Chưa rõ');
    });
  });
}
