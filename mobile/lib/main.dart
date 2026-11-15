import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/risk_colors.dart';
import 'core/widgets.dart';
import 'data/models/report.dart';
import 'data/models/road_segment.dart';
import 'data/services/api.dart';
import 'data/services/api_service.dart';
import 'features/forecast/forecast_screen.dart';
import 'features/map/map_screen.dart';
import 'features/map/segments_screen.dart';
import 'features/report/history_screen.dart';
import 'features/report/report_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final savedUrl = prefs.getString('api_url');
  if (savedUrl != null && savedUrl.isNotEmpty) {
    api.baseUrl = savedUrl;
  }
  runApp(const FloodApp());
}

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

  void _openServerSettings() {
    showDialog<void>(
      context: context,
      builder: (context) => ServerSettingsDialog(
        onSaved: _load,
      ),
    );
  }

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
                const SectionTitle('Cấu hình máy chủ'),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.dns_outlined),
                    title: const Text('Máy chủ API'),
                    subtitle: Text(api.baseUrl, style: const TextStyle(fontSize: 12)),
                    trailing: OutlinedButton(
                      onPressed: () {
                        Navigator.pop(context);
                        _openServerSettings();
                      },
                      child: const Text('Thay đổi'),
                    ),
                  ),
                ),
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

class ServerSettingsDialog extends StatefulWidget {
  final VoidCallback onSaved;

  const ServerSettingsDialog({super.key, required this.onSaved});

  @override
  State<ServerSettingsDialog> createState() => _ServerSettingsDialogState();
}

class _ServerSettingsDialogState extends State<ServerSettingsDialog> {
  late final TextEditingController _controller;
  bool _checking = false;
  String? _healthResult;
  bool _isError = false;
  String? _validationError;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: api.baseUrl);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _checkConnection() async {
    final err = ApiService.validateApiUrl(_controller.text);
    if (err != null) {
      setState(() {
        _validationError = err;
        _healthResult = null;
      });
      return;
    }

    setState(() {
      _validationError = null;
      _checking = true;
      _healthResult = null;
    });

    try {
      final res = await api.checkHealth(_controller.text);
      if (!mounted) return;
      final modelVer = res['model_version'] ?? 'Không rõ';
      setState(() {
        _healthResult = 'Kết nối thành công! Phiên bản mô hình: $modelVer';
        _isError = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _healthResult = '$e';
        _isError = true;
      });
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  void _useDefault() {
    setState(() {
      _controller.text = apiBaseUrl;
      _validationError = null;
      _healthResult = null;
    });
  }

  Future<void> _save() async {
    final err = ApiService.validateApiUrl(_controller.text);
    if (err != null) {
      setState(() {
        _validationError = err;
      });
      return;
    }

    final newUrl = ApiService.sanitizeApiUrl(_controller.text);
    api.baseUrl = newUrl;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_url', newUrl);

    if (!mounted) return;
    Navigator.of(context).pop();
    widget.onSaved();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Cấu hình Máy chủ'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _controller,
              decoration: InputDecoration(
                labelText: 'URL Máy chủ',
                hintText: 'http://192.168.1.10:8000',
                errorText: _validationError,
                border: const OutlineInputBorder(),
              ),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: _checking ? null : _checkConnection,
                  icon: _checking
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.network_check, size: 18),
                  label: const Text('Kiểm tra kết nối'),
                ),
                TextButton(
                  onPressed: _useDefault,
                  child: const Text('Dùng mặc định'),
                ),
              ],
            ),
            if (_healthResult != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: _isError
                      ? Theme.of(context).colorScheme.errorContainer
                      : Theme.of(context).colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      _isError ? Icons.error_outline : Icons.check_circle_outline,
                      color: _isError
                          ? Theme.of(context).colorScheme.onErrorContainer
                          : Theme.of(context).colorScheme.onPrimaryContainer,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _healthResult!,
                        style: TextStyle(
                          color: _isError
                              ? Theme.of(context).colorScheme.onErrorContainer
                              : Theme.of(context).colorScheme.onPrimaryContainer,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Hủy'),
        ),
        FilledButton(
          onPressed: _save,
          child: const Text('Lưu'),
        ),
      ],
    );
  }
}
