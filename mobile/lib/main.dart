import 'package:flutter/material.dart';

import 'core/risk_colors.dart';
import 'core/widgets.dart';
import 'data/models/report.dart';
import 'data/models/road_segment.dart';
import 'data/services/api.dart';
import 'features/forecast/forecast_screen.dart';
import 'features/map/map_screen.dart';
import 'features/map/segments_screen.dart';
import 'features/report/history_screen.dart';
import 'features/report/report_screen.dart';

void main() => runApp(const FloodApp());

ThemeData _theme(Brightness brightness) => ThemeData(
      colorScheme:
          ColorScheme.fromSeed(seedColor: const Color(0xFF0B6BCB), brightness: brightness),
      useMaterial3: true,
      cardTheme: CardThemeData(
        elevation: 1,
        margin: const EdgeInsets.symmetric(vertical: 4),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
    );

class FloodApp extends StatelessWidget {
  const FloodApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Cảnh báo mưa lớn Thủ Đức',
      debugShowCheckedModeBanner: false,
      theme: _theme(Brightness.light),
      darkTheme: _theme(Brightness.dark),
      home: const HomeScreen(),
    );
  }
}

/// Loads the risk map + community reports once and shares them with the three tabs.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  static const _titles = ['Bản đồ nguy cơ', 'Tuyến đường', 'Cộng đồng báo cáo'];

  RiskMap? _map;
  List<Report> _reports = [];
  String? _error;
  bool _loading = false;
  int? _horizon;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  /// Refreshes in place: the old data (and the map camera) stay while loading.
  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final (map, reports) = (
        await api.getRiskMap(horizon: _horizon),
        await api.getReports(),
      );
      if (!mounted) return;
      setState(() {
        _map = map;
        _reports = reports;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = '$e');
      if (_map != null) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openReport([RoadSegment? segment]) async {
    final sent = await Navigator.push<bool>(
        context, MaterialPageRoute(builder: (_) => ReportScreen(segment: segment)));
    if (sent == true) _load();
  }

  void _openForecast(RoadSegment segment) => Navigator.push(
      context,
      MaterialPageRoute<void>(
          builder: (_) => ForecastScreen(segment: segment, onReportSent: _load)));

  void _showInfo(RiskMap map) => showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        isScrollControlled: true,
        builder: (context) {
          final text = Theme.of(context).textTheme;
          return SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Về dự báo này', style: text.titleLarge),
                const SizedBox(height: 8),
                Text(map.disclaimer),
                const SizedBox(height: 8),
                const Text('Dự báo do mô hình học máy tính lại mỗi giờ từ số liệu thời tiết '
                    'Open-Meteo. Hiện mọi đoạn đường dùng chung một dự báo cho cả khu vực; '
                    'khác biệt giữa các đoạn đến từ báo cáo của người đi đường.'),
                const SectionTitle('Mức nguy cơ mưa lớn'),
                for (final item in map.legend)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(children: [
                      SizedBox(width: 120, child: Align(
                          alignment: Alignment.centerLeft, child: Pill.risk(item.level))),
                      Expanded(child: Text(riskSentence(item.level))),
                    ]),
                  ),
                const SectionTitle('Báo cáo cộng đồng'),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final level in floodLevels)
                    Pill(floodIcon(level), '${floodLabel(level)}: ${floodHint(level).toLowerCase()}',
                        floodColor(level)),
                ]),
                const SizedBox(height: 8),
                const Text('Báo cáo tự hết hạn sau 6 giờ để bản đồ không hiển thị tin cũ.'),
              ]),
            ),
          );
        },
      );

  @override
  Widget build(BuildContext context) {
    final map = _map;
    final activeReports = _reports.where((r) => r.active).length;
    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_tab]),
        actions: [
          IconButton(
            tooltip: 'Về dự báo này',
            onPressed: map == null ? null : () => _showInfo(map),
            icon: const Icon(Icons.info_outline),
          ),
          IconButton(
            tooltip: 'Làm mới',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: _loading && map != null
              ? const LinearProgressIndicator()
              : const SizedBox(height: 4),
        ),
      ),
      body: map == null
          ? (_error == null
              ? const Center(child: CircularProgressIndicator())
              : ErrorRetry(_error!, _load))
          : IndexedStack(index: _tab, children: [
              MapTab(
                map: map,
                reports: _reports,
                horizon: _horizon,
                onHorizon: (h) {
                  _horizon = h;
                  _load();
                },
                onForecast: _openForecast,
                onReport: _openReport,
              ),
              SegmentsTab(map: map, onTap: _openForecast),
              ReportList(reports: _reports, placeOf: map.segmentName, onRefresh: _load),
            ]),
      floatingActionButton: map == null || _tab == 1
          ? null
          : FloatingActionButton.extended(
              onPressed: _openReport,
              icon: const Icon(Icons.add_location_alt),
              label: const Text('Báo cáo'),
            ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: [
          const NavigationDestination(
              icon: Icon(Icons.map_outlined), selectedIcon: Icon(Icons.map), label: 'Bản đồ'),
          const NavigationDestination(icon: Icon(Icons.route), label: 'Tuyến đường'),
          NavigationDestination(
            icon: Badge(
              isLabelVisible: activeReports > 0,
              label: Text('$activeReports'),
              child: const Icon(Icons.groups_outlined),
            ),
            selectedIcon: const Icon(Icons.groups),
            label: 'Cộng đồng',
          ),
        ],
      ),
    );
  }
}
