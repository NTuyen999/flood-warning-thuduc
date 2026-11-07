import 'package:flutter/material.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final reports = [
      ['Ngập nhẹ', '10 phút trước', 'Chờ xác minh'],
      ['Không ngập', '1 giờ trước', 'Đã xác minh'],
      ['Ngập nặng', '5 giờ trước', 'Hết hạn'],
    ];
    return Scaffold(
      appBar: AppBar(title: const Text('Báo cáo gần đây')),
      body: ListView(
        children: [
          for (final r in reports)
            ListTile(
              leading: const Icon(Icons.report),
              title: Text(r[0]),
              subtitle: Text('Quan sát: ${r[1]}'),
              trailing: Chip(label: Text(r[2])),
            ),
        ],
      ),
    );
  }
}