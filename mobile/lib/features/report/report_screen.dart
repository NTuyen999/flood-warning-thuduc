import 'package:flutter/material.dart';

class ReportScreen extends StatefulWidget {
  const ReportScreen({super.key});

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  String status = 'Không ngập';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Gửi báo cáo')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            DropdownButtonFormField<String>(
              value: status,
              decoration: const InputDecoration(labelText: 'Tình trạng'),
              items: ['Không ngập', 'Ngập nhẹ', 'Ngập nặng']
                  .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                  .toList(),
              onChanged: (v) => setState(() => status = v!),
            ),
            const SizedBox(height: 12),
            const ListTile(
              leading: Icon(Icons.location_on),
              title: Text('Vị trí GPS (tự động)'),
              subtitle: Text('10.85, 106.77'),
            ),
            const ListTile(
              leading: Icon(Icons.access_time),
              title: Text('Thời điểm quan sát'),
              subtitle: Text('Bây giờ'),
            ),
            const TextField(
              maxLines: 3,
              decoration: InputDecoration(
                  labelText: 'Ghi chú', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.photo_camera),
              label: const Text('Thêm ảnh'),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Đã gửi (giả lập)')));
                Navigator.pop(context);
              },
              child: const Text('Gửi'),
            ),
          ],
        ),
      ),
    );
  }
}