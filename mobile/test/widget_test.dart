import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mobile/core/demo_mode.dart';
import 'package:mobile/core/widgets.dart';
import 'package:mobile/data/models/demo.dart';
import 'package:mobile/data/models/report.dart';
import 'package:mobile/data/models/road_segment.dart';
import 'package:mobile/data/services/api.dart';
import 'package:mobile/data/services/api_service.dart';
import 'package:mobile/features/map/map_screen.dart';
import 'package:mobile/features/report/history_screen.dart';
import 'package:mobile/features/report/report_screen.dart';
import 'package:mobile/features/route/route_screen.dart';
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
    var fullPath = options.path;
    if (options.queryParameters.isNotEmpty) {
      final queryStr = options.queryParameters.entries
          .where((e) => e.value != null)
          .map((e) => '${e.key}=${e.value}')
          .join('&');
      if (queryStr.isNotEmpty) {
        fullPath = '$fullPath?$queryStr';
      }
    }
    var route = routes['${options.method} $fullPath'];
    route ??= routes['${options.method} ${options.path}'];
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

final demoScenariosFixture = {
  'is_demo': true,
  'scenarios': [
    {'id': 'none', 'label': 'Không mưa', 'description': 'Khô ráo', 'rain_mm_per_h': 0.0, 'banner': 'Thời tiết khô ráo'},
    {'id': 'moderate', 'label': 'Mưa vừa', 'description': 'Mưa gia tăng', 'rain_mm_per_h': 18.5, 'banner': 'CẢNH BÁO MƯA VỪA'},
    {'id': 'heavy', 'label': 'Mưa nhiều', 'description': 'Mưa lớn', 'rain_mm_per_h': 45.0, 'banner': 'CẢNH BÁO MƯA LỚN NGUY HIỂM'},
  ],
};

final demoRoutePointsFixture = {
  'is_demo': true,
  'items': [
    {'id': 'P1', 'node_id': 'N_P1', 'name': 'Đầu Kha Vạn Cân (đoạn 1)', 'coordinates': [106.722805, 10.829985]},
    {'id': 'J2', 'node_id': 'N_J2', 'name': 'Ngã giao hẻm tắt (J2)', 'coordinates': [106.730421, 10.836188]},
    {'id': 'P2', 'node_id': 'N_P2', 'name': 'Cuối Kha Vạn Cân (đoạn 2)', 'coordinates': [106.734318, 10.838849]},
    {'id': 'H1', 'node_id': 'N_H1', 'name': 'Cuối hẻm cụt A (AL01)', 'coordinates': [106.731439, 10.838981]},
    {'id': 'H2', 'node_id': 'N_H2', 'name': 'Cuối hẻm cụt B (AL02)', 'coordinates': [106.723655, 10.832657]},
    {'id': 'H4', 'node_id': 'N_H4', 'name': 'Cuối hẻm cụt D (AL04)', 'coordinates': [106.726616, 10.831100]},
  ],
};

final demoMapHeavyFixture = {
  'type': 'FeatureCollection',
  'issued_at': '2026-11-12T09:00:00+07:00',
  'horizon': null,
  'stale': false,
  'model_version': 'demo-scenario',
  'disclaimer': 'Chỉ báo mô phỏng.',
  'legend': [
    {'level': 'green', 'label': 'Thấp', 'max_probability': 0.1},
    {'level': 'yellow', 'label': 'Trung bình', 'max_probability': 0.3},
    {'level': 'orange', 'label': 'Cao', 'max_probability': 0.6},
    {'level': 'red', 'label': 'Rất cao', 'max_probability': 1.0},
  ],
  'features': [
    {
      'type': 'Feature',
      'geometry': {'type': 'LineString', 'coordinates': [[106.72, 10.83], [106.73, 10.84]]},
      'properties': {
        'segment_id': 'SEG01',
        'name': 'Kha Vạn Cân (đoạn 1)',
        'probability': 0.55,
        'risk_level': 'orange',
        'report_summary': {'active': 0, 'flooded': 0, 'latest_at': null},
        'kind': 'main',
        'dead_end': false,
        'parent_segment_id': null,
        'level_source': 'own',
        'blocked': false,
        'is_demo': true,
      },
    },
    {
      'type': 'Feature',
      'geometry': {'type': 'LineString', 'coordinates': [[106.73, 10.84], [106.74, 10.85]]},
      'properties': {
        'segment_id': 'SEG02',
        'name': 'Kha Vạn Cân (đoạn 2)',
        'probability': 0.78,
        'risk_level': 'red',
        'report_summary': {'active': 1, 'flooded': 1, 'latest_at': '2026-11-12T09:15:00+07:00'},
        'kind': 'main',
        'dead_end': false,
        'parent_segment_id': null,
        'level_source': 'own',
        'blocked': true,
        'is_demo': true,
      },
    },
    {
      'type': 'Feature',
      'geometry': {'type': 'LineString', 'coordinates': [[106.732, 10.837], [106.731, 10.838]]},
      'properties': {
        'segment_id': 'AL01',
        'name': 'Hẻm 112 Kha Vạn Cân (Hẻm cụt A)',
        'probability': 0.07,
        'risk_level': 'red',
        'report_summary': {'active': 0, 'flooded': 0, 'latest_at': null},
        'kind': 'alley',
        'dead_end': true,
        'parent_segment_id': 'SEG02',
        'level_source': 'inherited:SEG02',
        'blocked': true,
        'is_demo': true,
      },
    },
  ],
  'is_demo': true,
};

final demoRouteOkFixture = {
  'status': 'ok',
  'scenario': 'none',
  'from_point': 'P1',
  'to_point': 'J2',
  'horizon': null,
  'recommended': {
    'length_m': 502.2,
    'eta_min': 1.0,
    'max_level': 'green',
    'edges': ['E_SEG01_4', 'E_SEG02_1'],
    'blocked_edges': [],
    'geometry': {'type': 'LineString', 'coordinates': [[106.722, 10.829], [106.730, 10.836]]},
  },
  'shortest': null,
  'messages': ['Tuyến đường thông suốt, không có đoạn bị cản trở nghiêm trọng.'],
  'disclaimer': 'Dữ liệu và kết quả định tuyến mang tính MÔ PHỎNG.',
  'is_demo': true,
};

final demoRouteDetourFixture = {
  'status': 'detour',
  'scenario': 'heavy',
  'from_point': 'P1',
  'to_point': 'J2',
  'horizon': null,
  'recommended': {
    'length_m': 1444.8,
    'eta_min': 2.9,
    'max_level': 'orange',
    'edges': ['E_SEG01_1', 'AL03'],
    'blocked_edges': [],
    'geometry': {'type': 'LineString', 'coordinates': [[106.722, 10.829], [106.730, 10.836]]},
  },
  'shortest': {
    'length_m': 1081.2,
    'eta_min': 2.2,
    'max_level': 'red',
    'edges': ['E_SEG02_1'],
    'blocked_edges': ['E_SEG02_1'],
    'geometry': {'type': 'LineString', 'coordinates': [[106.722, 10.829], [106.730, 10.836]]},
  },
  'messages': ['Đã tìm thấy tuyến đường vòng tránh các đoạn ngập lụt / nguy cơ cao.'],
  'disclaimer': 'Dữ liệu và kết quả định tuyến mang tính MÔ PHỎNG.',
  'is_demo': true,
};

final demoRouteUnreachableFixture = {
  'status': 'unreachable',
  'scenario': 'heavy',
  'from_point': 'P1',
  'to_point': 'P2',
  'horizon': null,
  'recommended': null,
  'shortest': {
    'length_m': 2000.0,
    'eta_min': 4.0,
    'max_level': 'red',
    'edges': ['E_SEG02_1'],
    'blocked_edges': ['E_SEG02_1'],
    'geometry': {'type': 'LineString', 'coordinates': [[106.722, 10.829], [106.734, 10.838]]},
  },
  'messages': ['Không tìm thấy tuyến đường thông suốt do có đoạn bị ngập nặng (mức Đỏ/bị chặn). Cân nhắc hoãn di chuyển.'],
  'disclaimer': 'Dữ liệu và kết quả định tuyến mang tính MÔ PHỎNG.',
  'is_demo': true,
};

FakeBackend useFakeBackend(WidgetTester tester) {
  demoMode.setEnabled(false);
  final backend = FakeBackend()
    ..routes.addAll({
      'GET /api/v1/map/risks': (200, risks),
      'GET /api/v1/reports': (200, reports),
      'GET /api/v1/forecast/SEG01': (200, forecast),
      'GET /api/v1/explain/SEG01': (200, explanation),
      'GET /api/v1/demo/scenarios': (200, demoScenariosFixture),
      'GET /api/v1/demo/route-points': (200, demoRoutePointsFixture),
      'GET /api/v1/demo/map?scenario=heavy': (200, demoMapHeavyFixture),
      'GET /api/v1/demo/map?scenario=none': (200, demoMapHeavyFixture),
      'GET /api/v1/demo/map?scenario=moderate': (200, demoMapHeavyFixture),
      'GET /api/v1/demo/forecast/SEG01?scenario=heavy': (200, forecast),
      'GET /api/v1/demo/route?scenario=none&from=P1&to=J2': (200, demoRouteOkFixture),
      'GET /api/v1/demo/route?scenario=heavy&from=P1&to=J2': (200, demoRouteDetourFixture),
      'GET /api/v1/demo/route?scenario=heavy&from=P1&to=P2': (200, demoRouteUnreachableFixture),
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

  group('server settings dialog', () {
    testWidgets('valid URL changes api.baseUrl and saves', (tester) async {
      SharedPreferences.setMockInitialValues({});
      final backend = useFakeBackend(tester);
      backend.routes['GET /health'] = (200, {'status': 'ok', 'model_version': 'xgb-final-1234'});
      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Về dự báo này'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Thay đổi'));
      await tester.pumpAndSettle();

      expect(find.text('Cấu hình Máy chủ'), findsOneWidget);

      await tester.enterText(find.byType(TextField), 'http://192.168.1.50:8000');
      await tester.tap(find.text('Kiểm tra kết nối'));
      await tester.pumpAndSettle();

      expect(find.textContaining('xgb-final-1234'), findsOneWidget);

      await tester.tap(find.text('Lưu'));
      await tester.pumpAndSettle();

      expect(api.baseUrl, 'http://192.168.1.50:8000');
    });

    testWidgets('invalid URL shows error and refuses to save', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Về dự báo này'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Thay đổi'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'invalid-url');
      await tester.tap(find.text('Lưu'));
      await tester.pumpAndSettle();

      expect(find.textContaining('URL phải bắt đầu bằng http:// hoặc https://'), findsOneWidget);
      expect(find.text('Cấu hình Máy chủ'), findsOneWidget);
    });

    testWidgets('health check failure displays error message', (tester) async {
      SharedPreferences.setMockInitialValues({});
      final backend = useFakeBackend(tester);
      backend.routes['GET /health'] = (503, {'detail': 'Máy chủ bảo trì'});

      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Về dự báo này'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Thay đổi'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Kiểm tra kết nối'));
      await tester.pumpAndSettle();

      expect(find.textContaining('Máy chủ bảo trì'), findsOneWidget);
    });
  });

  group('UX and stability (T5)', () {
    testWidgets('renders properly on small screen (360x640) without overflow', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      tester.view.physicalSize = const Size(360, 640);
      tester.view.devicePixelRatio = 1.0;
      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      expect(find.text('Bản đồ nguy cơ'), findsOneWidget);

      await tester.tap(find.text('Tuyến đường'));
      await tester.pumpAndSettle();
      expect(find.text('Kha Vạn Cân'), findsOneWidget);

      await tester.tap(find.text('Cộng đồng'));
      await tester.pumpAndSettle();
      expect(find.text('Ngập nhẹ'), findsOneWidget);
    });

    testWidgets('renders with large text scale factor (1.8) without overflow', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      await tester.pumpWidget(
        MediaQuery(
          data: const MediaQueryData(textScaler: TextScaler.linear(1.8)),
          child: const FloodApp(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Bản đồ nguy cơ'), findsOneWidget);
      await tester.tap(find.text('Tuyến đường'));
      await tester.pumpAndSettle();
      expect(find.text('Kha Vạn Cân'), findsOneWidget);
    });

    testWidgets('stale data displays warning banner', (tester) async {
      SharedPreferences.setMockInitialValues({});
      final backend = useFakeBackend(tester);
      final staleRisks = Map<String, Object?>.from(risks)..['stale'] = true;
      backend.routes['GET /api/v1/map/risks'] = (200, staleRisks);

      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      expect(find.textContaining('Dữ liệu cũ'), findsAtLeast(1));
    });

    testWidgets('report card handles report image network error smoothly', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      final reportWithImage = Report.fromJson({
        'id': 99,
        'segment_id': 'SEG01',
        'lat': 10.85,
        'lon': 106.77,
        'flood_level': 'heavy',
        'status': 'new',
        'age_minutes': 5,
        'note': 'Có ảnh đính kèm',
        'image_url': '/uploads/broken.jpg',
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ReportCard(reportWithImage, place: 'Kha Vạn Cân'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Ngập nặng'), findsOneWidget);
      expect(find.textContaining('Kha Vạn Cân'), findsOneWidget);
    });
  });

  group('simulation mode & routing (P6)', () {
    tearDown(() {
      demoMode.setEnabled(false);
    });

    test('parse demo models correctly', () {
      final scenario = DemoScenario.fromJson({
        'id': 'heavy',
        'label': 'Mưa nhiều',
        'description': 'Mưa lớn',
        'rain_mm_per_h': 45.0,
        'banner': 'CẢNH BÁO MƯA LỚN',
      });
      expect(scenario.id, 'heavy');
      expect(scenario.rainMmPerH, 45.0);

      final routePoint = RoutePoint.fromJson({
        'id': 'P1',
        'node_id': 'N_P1',
        'name': 'Đầu Kha Vạn Cân',
        'coordinates': [106.72, 10.82],
      });
      expect(routePoint.id, 'P1');
      expect(routePoint.coordinates.latitude, 10.82);

      final routeResult = RouteResult.fromJson({
        'status': 'detour',
        'scenario': 'heavy',
        'from_point': 'P1',
        'to_point': 'J2',
        'messages': ['Đường vòng tránh ngập'],
        'disclaimer': 'Mô phỏng',
        'is_demo': true,
        'recommended': {
          'length_m': 1400.0,
          'eta_min': 2.8,
          'max_level': 'orange',
          'edges': ['E1', 'E2'],
          'blocked_edges': [],
          'geometry': {
            'type': 'LineString',
            'coordinates': [
              [106.72, 10.82],
              [106.73, 10.83]
            ]
          }
        }
      });
      expect(routeResult.status, 'detour');
      expect(routeResult.recommended?.lengthM, 1400.0);
    });

    testWidgets('enabling simulation mode shows simulation top banner', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);
      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      expect(find.textContaining('ĐANG XEM DỮ LIỆU MÔ PHỎNG'), findsOneWidget);
    });

    testWidgets('switching scenario updates scenario chip and map header', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);
      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      expect(find.text('Mưa nhiều'), findsOneWidget);

      await tester.tap(find.text('Mưa vừa'));
      await tester.pumpAndSettle();

      expect(demoMode.value.scenario, 'moderate');
    });

    testWidgets('alley bottom sheet displays dead-end and blocked notice when tapped', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);
      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      final al01 = RoadSegment.fromFeature(
          (demoMapHeavyFixture['features'] as List)[2] as Map<String, dynamic>);
      final mapState = tester.state(find.byType(MapTab)) as dynamic;
      mapState.showSegment(al01);
      await tester.pumpAndSettle();

      expect(find.text('Hẻm 112 Kha Vạn Cân (Hẻm cụt A)'), findsOneWidget);
      expect(find.text('Hẻm cụt'), findsOneWidget);
      expect(find.textContaining('KHÔNG VÀO ĐƯỢC'), findsOneWidget);
    });

    testWidgets('RouteScreen displays ok status with success badge', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);
      demoMode.setScenario('none');
      await tester.pumpWidget(
        const MaterialApp(
          home: RouteScreen(initialFrom: 'P1', initialTo: 'J2'),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Tuyến thông suốt'), findsOneWidget);
      expect(find.textContaining('không có đoạn bị cản trở nghiêm trọng'), findsOneWidget);
    });

    testWidgets('RouteScreen displays detour status with detour badge', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);
      demoMode.setScenario('heavy');
      await tester.pumpWidget(
        const MaterialApp(
          home: RouteScreen(initialFrom: 'P1', initialTo: 'J2'),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Đường vòng tránh ngập'), findsOneWidget);
      expect(find.textContaining('tránh các đoạn ngập lụt'), findsOneWidget);
    });

    testWidgets('RouteScreen displays unreachable status with blocked badge', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);
      demoMode.setScenario('heavy');
      await tester.pumpWidget(
        const MaterialApp(
          home: RouteScreen(initialFrom: 'P1', initialTo: 'P2'),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Không thể di chuyển'), findsOneWidget);
      expect(find.textContaining('Không tìm thấy tuyến đường thông suốt'), findsOneWidget);
    });

    testWidgets('disclaimer is always present on RouteScreen result card', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);
      await tester.pumpWidget(
        const MaterialApp(
          home: RouteScreen(initialFrom: 'P1', initialTo: 'J2'),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('mang tính MÔ PHỎNG'), findsOneWidget);
    });

    testWidgets('disabling simulation mode restores real map data', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);
      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      expect(find.textContaining('ĐANG XEM DỮ LIỆU MÔ PHỎNG'), findsOneWidget);

      demoMode.setEnabled(false);
      await tester.pumpAndSettle();

      expect(find.textContaining('ĐANG XEM DỮ LIỆU MÔ PHỎNG'), findsNothing);
      expect(find.text('Nguy cơ mưa lớn: Rất cao'), findsOneWidget);
    });

    testWidgets('RouteScreen renders cleanly without overflow on small screen (360x640)', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);
      tester.view.physicalSize = const Size(360, 640);
      tester.view.devicePixelRatio = 1.0;

      await tester.pumpWidget(
        const MaterialApp(
          home: RouteScreen(initialFrom: 'P1', initialTo: 'J2'),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Gợi ý đường đi (Mô phỏng)'), findsOneWidget);
      expect(find.text('Đường vòng tránh ngập'), findsOneWidget);
    });

    testWidgets('RouteScreen renders cleanly with large text scale factor (1.8)', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(true);

      await tester.pumpWidget(
        MediaQuery(
          data: const MediaQueryData(textScaler: TextScaler.linear(1.8)),
          child: const MaterialApp(
            home: RouteScreen(initialFrom: 'P1', initialTo: 'J2'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Gợi ý đường đi (Mô phỏng)'), findsOneWidget);
    });

    testWidgets('tapping route button when simulation mode is off prompts dialog', (tester) async {
      SharedPreferences.setMockInitialValues({});
      useFakeBackend(tester);
      demoMode.setEnabled(false);
      await tester.pumpWidget(const FloodApp());
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Gợi ý đường đi'));
      await tester.pumpAndSettle();

      expect(find.text('Gợi ý đường đi'), findsOneWidget);
      expect(find.text('Bật chế độ mô phỏng'), findsOneWidget);

      await tester.tap(find.text('Bật chế độ mô phỏng'));
      await tester.pumpAndSettle();

      expect(demoMode.value.enabled, isTrue);
      expect(find.text('Gợi ý đường đi (Mô phỏng)'), findsOneWidget);
    });
  });
}
