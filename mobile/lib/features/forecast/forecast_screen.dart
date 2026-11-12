import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/risk_colors.dart';
import '../../core/widgets.dart';
import '../../data/models/forecast.dart';
import '../../data/models/report.dart';
import '../../data/models/road_segment.dart';
import '../../data/services/api.dart';
import '../explain/explain_screen.dart';
import '../report/history_screen.dart';
import '../report/report_screen.dart';

final _hm = DateFormat('HH:mm');

class ForecastScreen extends StatefulWidget {
  final RoadSegment segment;

  /// Called after the user sent a report from here, so the home data reloads.
  final VoidCallback onReportSent;

  const ForecastScreen({super.key, required this.segment, required this.onReportSent});

  @override
  State<ForecastScreen> createState() => _ForecastScreenState();
}

class _ForecastScreenState extends State<ForecastScreen> {
  late Future<(Forecast, Weather?, List<Report>)> _future = _load();

  Future<(Forecast, Weather?, List<Report>)> _load() async {
    final id = widget.segment.id;
    // Weather and reports are extras: the forecast still shows when they fail.
    final weather = api.getWeather().then<Weather?>((w) => w).catchError((_) => null);
    final reports = api.getReports(segmentId: id).catchError((_) => <Report>[]);
    return (await api.getForecast(id), await weather, await reports);
  }

  Future<void> _reload() {
    // Block body on purpose: an arrow closure would return the Future and setState rejects that.
    setState(() {
      _future = _load();
    });
    return _future.then((_) {}, onError: (_) {});
  }

  void _explain(Forecast f, int horizon) => Navigator.push(
      context,
      MaterialPageRoute<void>(
          builder: (_) => ExplainScreen(segment: widget.segment, forecast: f, horizon: horizon)));

  Future<void> _report() async {
    final sent = await Navigator.push<bool>(
        context, MaterialPageRoute(builder: (_) => ReportScreen(segment: widget.segment)));
    if (sent == true) {
      widget.onReportSent();
      _reload();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.segment.name)),
      body: LoadView(
        future: _future,
        onRetry: _reload,
        builder: (context, data) {
          final (f, weather, reports) = data;
          final worst = f.worst;
          return RefreshIndicator(
            onRefresh: _reload,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                _Summary(f),
                if (weather != null) _WeatherRow(weather),
                const SectionTitle('Khả năng mưa lớn theo giờ'),
                _HourBars(f, onTap: (h) => _explain(f, h)),
                const SizedBox(height: 4),
                Text('Chạm vào một cột để xem vì sao có mức đó.',
                    style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 16),
                Row(children: [
                  Expanded(
                    child: FilledButton.tonalIcon(
                      onPressed: worst == null ? null : () => _explain(f, worst.h),
                      icon: const Icon(Icons.insights),
                      label: const Text('Vì sao?'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: _report,
                      icon: const Icon(Icons.add_location_alt),
                      label: const Text('Báo cáo tại đây'),
                    ),
                  ),
                ]),
                const SectionTitle('Người đi đường báo cáo'),
                if (reports.isEmpty)
                  const Text('Chưa có báo cáo nào trên đoạn này. Đang ở đây? Hãy báo cáo để giúp mọi người.')
                else
                  for (final r in reports.take(5)) ReportCard(r, place: widget.segment.name),
                const SizedBox(height: 16),
                Text(f.disclaimer, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  final Forecast f;

  const _Summary(this.f);

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final worst = f.worst;
    final level = worst?.level;
    final color = riskColor(level);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(riskIcon(level), size: 44, color: color),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Nguy cơ mưa lớn 6 giờ tới', style: text.labelLarge),
              Text(riskLabel(level), style: text.headlineMedium),
            ]),
          ),
        ]),
        const SizedBox(height: 8),
        Text(riskSentence(level), style: text.bodyLarge),
        if (worst != null && level != 'green')
          Text('Cao nhất khoảng ${_hm.format(f.timeOf(worst.h))} (${percent(worst.probability)}).'),
        const SizedBox(height: 8),
        Text('Cập nhật lúc ${DateFormat('HH:mm dd/MM').format(f.issuedAt)}', style: text.bodySmall),
        if (f.stale)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Pill(Icons.history, 'Dữ liệu cũ: nguồn thời tiết đang lỗi', Colors.blueGrey),
          ),
      ]),
    );
  }
}

class _WeatherRow extends StatelessWidget {
  final Weather w;

  const _WeatherRow(this.w);

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    Widget stat(IconData icon, String value, String label) => Expanded(
          child: Column(children: [
            Icon(icon, color: Theme.of(context).colorScheme.primary),
            Text(value, style: text.titleMedium),
            Text(label, style: text.bodySmall),
          ]),
        );
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(children: [
        Row(children: [
          stat(Icons.thermostat, '${w.temperature.toStringAsFixed(1)}°C', 'Nhiệt độ'),
          stat(Icons.water_drop_outlined, '${w.humidity.round()}%', 'Độ ẩm'),
          stat(Icons.grain, '${w.precipitation.toStringAsFixed(1)} mm', 'Mưa 1 giờ'),
          stat(Icons.air, '${w.windSpeed.round()} km/h', 'Gió'),
        ]),
        const SizedBox(height: 4),
        Text('Thời tiết lúc ${_hm.format(w.observedAt)} (số liệu mô hình Open-Meteo)',
            style: text.bodySmall),
      ]),
    );
  }
}

/// Six bars, one per forecast hour. Plain widgets so each bar has a text value
/// and a screen-reader label, and stays visible when the probability is ~0.
class _HourBars extends StatelessWidget {
  final Forecast f;
  final void Function(int horizon) onTap;

  const _HourBars(this.f, {required this.onTap});

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return SizedBox(
      height: 190,
      child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        for (final h in f.horizons)
          Expanded(
            child: Semantics(
              button: true,
              label: 'Lúc ${_hm.format(f.timeOf(h.h))}, khả năng ${percent(h.probability)}, '
                  'mức ${riskLabel(h.level)}',
              excludeSemantics: true,
              child: InkWell(
                onTap: () => onTap(h.h),
                borderRadius: BorderRadius.circular(8),
                child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
                  Text(percent(h.probability), style: text.labelMedium),
                  const SizedBox(height: 4),
                  // Faint full-height track, so near-zero bars still read as a chart.
                  Container(
                    height: 128,
                    margin: const EdgeInsets.symmetric(horizontal: 8),
                    alignment: Alignment.bottomCenter,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Container(
                      height: 8 + 120 * h.probability,
                      width: double.infinity,
                      decoration: BoxDecoration(
                        color: riskColor(h.level),
                        borderRadius: BorderRadius.circular(6),
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(_hm.format(f.timeOf(h.h)), style: text.bodySmall),
                ]),
              ),
            ),
          ),
      ]),
    );
  }
}
