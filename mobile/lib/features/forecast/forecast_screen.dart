import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../core/risk_colors.dart';
import '../../data/models/forecast.dart';
import '../../data/models/road_segment.dart';
import '../../data/services/api.dart';
import '../explain/explain_screen.dart';
import '../report/history_screen.dart';

class ForecastScreen extends StatefulWidget {
  final RoadSegment segment;
  const ForecastScreen({super.key, required this.segment});

  @override
  State<ForecastScreen> createState() => _ForecastScreenState();
}

class _ForecastScreenState extends State<ForecastScreen> {
  late Future<Forecast> _future = api.getForecast(widget.segment.id);

  void _retry() => setState(() => _future = api.getForecast(widget.segment.id));

  String _worstLevel(Forecast f) => f.horizons
      .map((h) => h.level)
      .reduce((a, b) => riskOrder.indexOf(a) >= riskOrder.indexOf(b) ? a : b);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.segment.name)),
      body: FutureBuilder<Forecast>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text('Không tải được dự báo\n${snap.error}',
                    textAlign: TextAlign.center),
                const SizedBox(height: 12),
                FilledButton(onPressed: _retry, child: const Text('Thử lại')),
              ]),
            );
          }
          final f = snap.data!;
          final worst = _worstLevel(f);
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Row(children: [
                Chip(
                  avatar: CircleAvatar(backgroundColor: riskColor(worst)),
                  label: Text('Cao nhất 6h tới: ${riskLabel(worst)}'),
                ),
                const SizedBox(width: 8),
                if (f.isMock) const Chip(label: Text('Dữ liệu mô phỏng')),
              ]),
              const SizedBox(height: 4),
              Text('Phát hành: ${DateFormat('HH:mm dd/MM/yyyy').format(f.issuedAt.toLocal())}',
                  style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 16),
              const Text('Nguy cơ mưa lớn 1–6 giờ tới',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              SizedBox(height: 220, child: _chart(f)),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: () => Navigator.push(context,
                    MaterialPageRoute(builder: (_) => const ExplainScreen())),
                child: const Text('Tại sao cảnh báo?'),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: () => Navigator.push(context,
                    MaterialPageRoute(builder: (_) => const HistoryScreen())),
                child: const Text('Xem báo cáo cộng đồng'),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _chart(Forecast f) {
    return BarChart(
      BarChartData(
        minY: 0,
        maxY: 1,
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              interval: 0.25,
              getTitlesWidget: (v, meta) => Text('${(v * 100).toInt()}%'),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (v, meta) => Text('+${f.horizons[v.toInt()].h}h'),
            ),
          ),
        ),
        barGroups: [
          for (var i = 0; i < f.horizons.length; i++)
            BarChartGroupData(x: i, barRods: [
              BarChartRodData(
                toY: f.horizons[i].probability,
                color: riskColor(f.horizons[i].level),
                width: 24,
                borderRadius: BorderRadius.circular(4),
              ),
            ]),
        ],
      ),
    );
  }
}