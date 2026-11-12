import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/widgets.dart';
import 'package:mobile/data/models/road_segment.dart';
import 'package:mobile/data/services/api.dart';
import 'package:mobile/data/services/api_service.dart';
import 'package:mobile/features/report/report_screen.dart';
import 'package:mobile/main.dart';

/// Answers Dio requests from a "METHOD /path" -> (status, json) table, like the backend.
/// A missing route behaves like a dead network.
class FakeBackend implements HttpClientAdapter {
  final routes = <String, (int, Object)>{};
  final requests = <RequestOptions>[];

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream,
      Future<void>? cancelFuture) async {
    requests.add(options);
    final route = routes['${options.method} ${options.path}'];
    if (route == null) throw DioException.connectionError(requestOptions: options, reason: 'down');
    return ResponseBody.fromString(jsonEncode(route.$2), route.$1, headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    });
  }

  @override
  void close({bool force = false}) {}
}

Map<String, Object?> segmentFeature(String id, String name, {int active = 0, int flooded = 0}) => {
      'type': 'Feature',
      'geometry': {
        'type': 'LineString',
        'coordinates': [[106.76, 10.85], [106.77, 10.851], [106.78, 10.852]],
      },
      'properties': {
        'segment_id': id,
        'name': name,
        'probability': 0.66,
        'risk_level': 'red',
        'report_summary': {'active': active, 'flooded': flooded, 'latest_at': null},
      },
    };

final risks = {
  'issued_at': '2026-11-12T09:00:00+07:00',
  'stale': false,
  'disclaimer': 'Chỉ báo sớm, chưa kiểm chứng.',
  'legend': [
    {'level': 'green', 'label': 'Thấp', 'max_probability': 0.1},
    {'level': 'yellow', 'label': 'Trung bình', 'max_probability': 0.3},
    {'level': 'orange', 'label': 'Cao', 'max_probability': 0.6},
    {'level': 'red', 'label': 'Rất cao', 'max_probability': 1.0},
  ],
  'features': [
    segmentFeature('SEG01', 'Võ Văn Ngân'),
    segmentFeature('SEG02', 'Kha Vạn Cân', active: 2, flooded: 1),
  ],
};

final forecast = {
  'segment_id': 'SEG01',
  'issued_at': '2026-11-12T09:00:00+07:00',
  'stale': false,
  'disclaimer': 'Chỉ báo sớm, chưa kiểm chứng.',
  'horizons': [
    for (final (i, p) in [0.004, 0.12, 0.31, 0.48, 0.66, 0.40].indexed)
      {'h': i + 1, 'probability': p, 'level': ['green', 'yellow', 'orange', 'orange', 'red', 'orange'][i]},
  ],
};

final explanation = {
  'probability': 0.66,
  'level': 'red',
  'note': 'SHAP, không phải nhân quả.',
  'features': [
    {'label': 'Tổng mưa 3 giờ qua', 'impact': 1.2, 'text': 'Tổng mưa 3 giờ qua = 12.5 mm → làm tăng nguy cơ'},
    {'label': 'Độ ẩm tương đối', 'impact': -0.3, 'text': 'Độ ẩm tương đối = 90% → làm giảm nguy cơ'},
  ],
};

final reports = {
  'items': [
    {'id': 1, 'segment_id': 'SEG02', 'lat': 10.851, 'lon': 106.77, 'flood_level': 'light',
      'status': 'new', 'age_minutes': 12, 'note': 'Ngập tới mắt cá', 'image_url': null},
    {'id': 2, 'segment_id': null, 'lat': 10.80, 'lon': 106.75, 'flood_level': 'heavy',
      'status': 'expired', 'age_minutes': 400, 'note': null, 'image_url': null},
  ],
};

FakeBackend useFakeBackend(WidgetTester tester) {
  final backend = FakeBackend()
    ..routes.addAll({
      'GET /api/v1/map/risks': (200, risks),
      'GET /api/v1/reports': (200, reports),
      'GET /api/v1/forecast/SEG01': (200, forecast),
      'GET /api/v1/explain/SEG01': (200, explanation),
    });
  api = ApiService(Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = backend);
  BaseMap.tiles = false;
  tester.view.physicalSize = const Size(1080, 2400); // tall phone: whole screens are on stage
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
  return backend;
}

void main() {
  testWidgets('map -> road list -> forecast -> explanation, all from the API', (tester) async {
    useFakeBackend(tester);
    await tester.pumpWidget(const FloodApp());
    await tester.pumpAndSettle();

    expect(find.text('Bản đồ nguy cơ'), findsOneWidget);
    expect(find.text('Nguy cơ mưa lớn: Rất cao'), findsOneWidget);
    expect(find.text('≥60%'), findsOneWidget); // legend built from the API's bands

    await tester.tap(find.text('Tuyến đường'));
    await tester.pumpAndSettle();
    expect(find.textContaining('1 báo cáo ngập'), findsOneWidget);
    // The road with flood reports is listed first.
    expect(tester.getTopLeft(find.text('Kha Vạn Cân')).dy,
        lessThan(tester.getTopLeft(find.text('Võ Văn Ngân')).dy));

    await tester.tap(find.text('Võ Văn Ngân'));
    await tester.pumpAndSettle();
    expect(find.text('Rất cao'), findsOneWidget); // worst of the six hours
    expect(find.text('<1%'), findsOneWidget); // 0.4% stays readable
    // Weather is optional: this fake backend has no weather route, the forecast still shows.
    expect(find.text('Nhiệt độ'), findsNothing);

    await tester.tap(find.text('66%'));
    await tester.pumpAndSettle();
    expect(find.text('Tổng mưa 3 giờ qua = 12.5 mm → làm tăng nguy cơ'), findsOneWidget);
    expect(find.textContaining('Yếu tố ảnh hưởng nhiều nhất: Tổng mưa 3 giờ qua'), findsOneWidget);
  });

  testWidgets('community tab hides expired reports until asked', (tester) async {
    useFakeBackend(tester);
    await tester.pumpWidget(const FloodApp());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cộng đồng'));
    await tester.pumpAndSettle();

    expect(find.text('Ngập nhẹ'), findsOneWidget);
    expect(find.textContaining('Kha Vạn Cân · 12 phút trước'), findsOneWidget);
    expect(find.text('Ngập nặng'), findsNothing);

    await tester.tap(find.text('Tất cả'));
    await tester.pumpAndSettle();
    expect(find.text('Ngập nặng'), findsOneWidget);
    expect(find.text('Hết hạn'), findsOneWidget);
  });

  testWidgets('backend down shows a retry screen, then recovers', (tester) async {
    final backend = useFakeBackend(tester);
    final saved = backend.routes.remove('GET /api/v1/map/risks')!;
    await tester.pumpWidget(const FloodApp());
    await tester.pumpAndSettle();
    expect(find.textContaining('Không kết nối được máy chủ'), findsOneWidget);

    backend.routes['GET /api/v1/map/risks'] = saved;
    await tester.tap(find.text('Thử lại'));
    await tester.pumpAndSettle();
    expect(find.text('Nguy cơ mưa lớn: Rất cao'), findsOneWidget);
  });

  testWidgets('a report sent from the forecast screen appears there right away', (tester) async {
    final backend = useFakeBackend(tester);
    backend.routes['GET /api/v1/reports'] = (200, {'items': <Object>[]});
    backend.routes['POST /api/v1/reports'] = (201, reports['items']![0]);
    await tester.pumpWidget(const FloodApp());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Tuyến đường'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Võ Văn Ngân'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Chưa có báo cáo nào trên đoạn này'), findsOneWidget);

    await tester.tap(find.text('Báo cáo tại đây'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ngập nhẹ'));
    await tester.pumpAndSettle();
    backend.routes['GET /api/v1/reports'] = (200, reports); // the server now has it
    await tester.tap(find.text('Gửi báo cáo'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Chưa có báo cáo nào trên đoạn này'), findsNothing);
    expect(find.textContaining('12 phút trước'), findsOneWidget);
  });

  group('report form', () {
    final segment = RoadSegment.fromFeature(segmentFeature('SEG01', 'Võ Văn Ngân'));

    Future<List<bool?>> openForm(WidgetTester tester) async {
      final results = <bool?>[];
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () async => results.add(await Navigator.push<bool>(context,
                  MaterialPageRoute(builder: (_) => ReportScreen(segment: segment)))),
              child: const Text('open'),
            ),
          ),
        ),
      ));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();
      return results;
    }

    testWidgets('sends the chosen level at the pinned place', (tester) async {
      final backend = useFakeBackend(tester);
      backend.routes['POST /api/v1/reports'] = (201, reports['items']![0]);
      final results = await openForm(tester);

      // Nothing can be sent before a level is chosen.
      await tester.tap(find.text('Chọn tình trạng đường để gửi'));
      await tester.pumpAndSettle();
      expect(backend.requests.where((r) => r.method == 'POST'), isEmpty);

      await tester.tap(find.text('Ngập nặng'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Gửi báo cáo'));
      await tester.pumpAndSettle();

      final sent = backend.requests.singleWhere((r) => r.method == 'POST').data as Map;
      expect(sent['flood_level'], 'heavy');
      expect(sent['lat'], segment.middle.latitude);
      expect(sent['lon'], segment.middle.longitude);
      expect(sent.containsKey('image_url'), isFalse);
      expect(results, [true]);
      expect(find.text('Đã gửi báo cáo. Cảm ơn bạn!'), findsOneWidget);
    });

    testWidgets('a duplicate (409) is explained, not shown as an error', (tester) async {
      final backend = useFakeBackend(tester);
      backend.routes['POST /api/v1/reports'] =
          (409, {'detail': {'message': 'Đã có báo cáo tương tự gần đây', 'duplicate_of': 1}});
      final results = await openForm(tester);
      await tester.tap(find.text('Không ngập'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Gửi báo cáo'));
      await tester.pumpAndSettle();
      expect(find.text('Đã có người báo cáo'), findsOneWidget);

      await tester.tap(find.text('Đã hiểu'));
      await tester.pumpAndSettle();
      expect(results, [false]);
    });

    testWidgets('a rejected report (422) keeps the form and shows the server reason',
        (tester) async {
      final backend = useFakeBackend(tester);
      backend.routes['POST /api/v1/reports'] = (422, {
        'detail': [{'msg': 'Value error, Vị trí nằm ngoài TP Thủ Đức', 'type': 'value_error'}],
      });
      final results = await openForm(tester);
      await tester.tap(find.text('Ngập nhẹ'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Gửi báo cáo'));
      await tester.pumpAndSettle();
      expect(find.text('Vị trí nằm ngoài TP Thủ Đức'), findsOneWidget);
      expect(results, isEmpty); // still on the form
    });
  });
}
