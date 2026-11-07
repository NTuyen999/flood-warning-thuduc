import 'package:flutter/material.dart';

class ExplainScreen extends StatelessWidget {
  const ExplainScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final items = {
      'Lượng mưa 3h gần nhất': 0.8,
      'Lượng mưa 1h gần nhất': 0.6,
      'Độ ẩm tương đối': 0.4,
      'CAPE (năng lượng đối lưu)': 0.3,
      'Xu hướng áp suất': 0.2,
    };
    return Scaffold(
      appBar: AppBar(title: const Text('Tại sao cảnh báo?')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Các yếu tố mô hình dựa vào nhiều nhất:',
                style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            for (final e in items.entries) ...[
              Text(e.key),
              LinearProgressIndicator(value: e.value, minHeight: 10),
              const SizedBox(height: 12),
            ],
            const Spacer(),
            const Text(
              'Lưu ý: đây là các yếu tố mô hình sử dụng để dự báo, không phải nguyên nhân chắc chắn.',
              style: TextStyle(fontStyle: FontStyle.italic),
            ),
          ],
        ),
      ),
    );
  }
}