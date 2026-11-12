import 'dart:math';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/risk_colors.dart';
import '../../core/widgets.dart';
import '../../data/models/forecast.dart';
import '../../data/models/road_segment.dart';
import '../../data/services/api.dart';

const _up = Color(0xFFD93025);
const _down = Color(0xFF2E9E5B);

/// "Why this risk?": the model's top SHAP factors for one forecast hour.
class ExplainScreen extends StatefulWidget {
  final RoadSegment segment;
  final Forecast forecast;
  final int horizon;

  const ExplainScreen(
      {super.key, required this.segment, required this.forecast, required this.horizon});

  @override
  State<ExplainScreen> createState() => _ExplainScreenState();
}

class _ExplainScreenState extends State<ExplainScreen> {
  late int _horizon = widget.horizon;
  late Future<Explanation> _future = api.getExplanation(widget.segment.id, _horizon);

  void _load([int? horizon]) => setState(() {
        _horizon = horizon ?? _horizon;
        _future = api.getExplanation(widget.segment.id, _horizon);
      });

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final hm = DateFormat('HH:mm');
    return Scaffold(
      appBar: AppBar(title: const Text('Vì sao có mức này?')),
      body: Column(children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(children: [
            for (final h in widget.forecast.horizons)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: ChoiceChip(
                  label: Text(hm.format(widget.forecast.timeOf(h.h))),
                  selected: h.h == _horizon,
                  onSelected: (_) => _load(h.h),
                ),
              ),
          ]),
        ),
        Expanded(
          child: LoadView(
            future: _future,
            onRetry: _load,
            builder: (context, e) {
              final scale = e.features.map((f) => f.impact.abs()).fold(0.0, max);
              return ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                children: [
                  Row(children: [
                    Pill.risk(e.level),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Khả năng mưa lớn lúc ${hm.format(widget.forecast.timeOf(_horizon))}: '
                        '${percent(e.probability)}',
                        style: text.titleMedium,
                      ),
                    ),
                  ]),
                  if (e.features.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text('Yếu tố ảnh hưởng nhiều nhất: ${e.features.first.text}.',
                        style: text.bodyLarge),
                  ],
                  const SectionTitle('Các yếu tố mô hình dựa vào'),
                  for (final f in e.features) _FactorBar(f, scale),
                  const SizedBox(height: 8),
                  const Wrap(spacing: 16, children: [
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(Icons.square, size: 14, color: _down),
                      Text(' Làm giảm nguy cơ'),
                    ]),
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(Icons.square, size: 14, color: _up),
                      Text(' Làm tăng nguy cơ'),
                    ]),
                  ]),
                  const SizedBox(height: 16),
                  Text(e.note, style: text.bodySmall),
                ],
              );
            },
          ),
        ),
      ]),
    );
  }
}

/// Bar growing left (lowers the risk) or right (raises it) from the centre line.
class _FactorBar extends StatelessWidget {
  final ExplainFeature f;
  final double scale;

  const _FactorBar(this.f, this.scale);

  @override
  Widget build(BuildContext context) {
    final raises = f.impact > 0;
    final share = scale == 0 ? 0.0 : f.impact.abs() / scale;
    Widget half(bool active, Alignment align) => Expanded(
          child: Align(
            alignment: align,
            child: FractionallySizedBox(
              widthFactor: active ? max(share, 0.03) : 0,
              child: Container(
                height: 14,
                decoration: BoxDecoration(
                  color: raises ? _up : _down,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ),
          ),
        );
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Semantics(
        label: f.text,
        excludeSemantics: true,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(f.text),
          const SizedBox(height: 4),
          Row(children: [
            half(!raises, Alignment.centerRight),
            Container(width: 2, height: 22, color: Theme.of(context).colorScheme.outline),
            half(raises, Alignment.centerLeft),
          ]),
        ]),
      ),
    );
  }
}
