import 'package:flutter/material.dart';

void main() => runApp(const FloodApp());

class FloodApp extends StatelessWidget {
  const FloodApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Cảnh báo nguy cơ mưa lớn - Thủ Đức',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.blue, useMaterial3: true),
      home: const MapScreen(),
    );
  }
}

// ---------- 1. MAP ----------
class MapScreen extends StatelessWidget {
  const MapScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final segments = ['Đoạn 01 - Võ Văn Ngân', 'Đoạn 02 - Kha Vạn Cân', 'Đoạn 03 - Xa lộ Hà Nội'];
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bản đồ nguy cơ'),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () => Navigator.push(
                context, MaterialPageRoute(builder: (_) => const HistoryScreen())),
          ),
        ],
      ),
      body: Stack(
        children: [
          Container(
            color: Colors.grey.shade300,
            child: const Center(child: Text('[ Bản đồ + road segments ]\n(làm ở MB03)', textAlign: TextAlign.center)),
          ),
          Positioned(
            top: 12,
            right: 12,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: const [
                  Text('● Thấp', style: TextStyle(color: Colors.green)),
                  Text('● Trung bình', style: TextStyle(color: Colors.amber)),
                  Text('● Cao', style: TextStyle(color: Colors.orange)),
                  Text('● Rất cao', style: TextStyle(color: Colors.red)),
                ]),
              ),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Material(
              color: Colors.white,
              child: SizedBox(
                height: 170,
                child: ListView(
                  children: [
                    const Padding(
                      padding: EdgeInsets.all(8),
                      child: Text('Chạm một đoạn đường (giả lập):'),
                    ),
                    for (final s in segments)
                      ListTile(
                        title: Text(s),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (_) => DetailScreen(name: s))),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(bottom: 170),
        child: FloatingActionButton.extended(
          icon: const Icon(Icons.add),
          label: const Text('Báo cáo'),
          onPressed: () => Navigator.push(
              context, MaterialPageRoute(builder: (_) => const ReportScreen())),
        ),
      ),
    );
  }
}

// ---------- 2. CHI TIẾT + FORECAST ----------
class DetailScreen extends StatelessWidget {
  final String name;
  const DetailScreen({super.key, required this.name});

  @override
  Widget build(BuildContext context) {
    final risks = [0.1, 0.2, 0.4, 0.6, 0.7, 0.5];
    return Scaffold(
      appBar: AppBar(title: Text(name)),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Chip(label: Text('Hiện tại: Trung bình')),
            const SizedBox(height: 16),
            const Text('Nguy cơ mưa lớn 1–6 giờ tới', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            SizedBox(
              height: 150,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  for (var i = 0; i < 6; i++)
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          Container(
                            height: 120 * risks[i],
                            margin: const EdgeInsets.symmetric(horizontal: 6),
                            color: Colors.orange,
                          ),
                          Text('+${i + 1}h'),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => Navigator.push(
                  context, MaterialPageRoute(builder: (_) => const ExplainScreen())),
              child: const Text('Tại sao cảnh báo?'),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: () => Navigator.push(
                  context, MaterialPageRoute(builder: (_) => const HistoryScreen())),
              child: const Text('Xem báo cáo cộng đồng'),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------- 3. GỬI BÁO CÁO ----------
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
              decoration: InputDecoration(labelText: 'Ghi chú', border: OutlineInputBorder()),
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
                ScaffoldMessenger.of(context)
                    .showSnackBar(const SnackBar(content: Text('Đã gửi (giả lập)')));
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

// ---------- 4. GIẢI THÍCH ----------
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
            const Text('Các yếu tố mô hình dựa vào nhiều nhất:', style: TextStyle(fontWeight: FontWeight.bold)),
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

// ---------- 5. LỊCH SỬ BÁO CÁO ----------
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