import 'package:flutter/material.dart';

// Risk level of the heavy-rain forecast. Always shown as colour + icon + text,
// so it stays readable for colour-blind users.

Color riskColor(String? level) => switch (level) {
  'green' => const Color(0xFF2E9E5B),
  'yellow' => const Color(0xFFE5A800),
  'orange' => const Color(0xFFF07C1B),
  'red' => const Color(0xFFD93025),
  _ => Colors.blueGrey,
};

IconData riskIcon(String? level) => switch (level) {
  'green' => Icons.check_circle,
  'yellow' => Icons.water_drop,
  'orange' => Icons.warning_amber_rounded,
  'red' => Icons.thunderstorm,
  _ => Icons.help_outline,
};

const riskOrder = ['green', 'yellow', 'orange', 'red'];

String riskLabel(String? level) => switch (level) {
  'green' => 'Thấp',
  'yellow' => 'Trung bình',
  'orange' => 'Cao',
  'red' => 'Rất cao',
  _ => 'Chưa rõ',
};

String riskSentence(String? level) => switch (level) {
  'green' => 'Gần như không có khả năng mưa lớn.',
  'yellow' => 'Có thể có mưa lớn, nên theo dõi thêm.',
  'orange' => 'Khả năng mưa lớn cao, cân nhắc đổi giờ đi hoặc lộ trình.',
  'red' => 'Rất dễ có mưa lớn, tránh các đoạn đường trũng.',
  _ => 'Chưa có dự báo cho đoạn này.',
};

String percent(double p) => p < 0.01 ? '<1%' : '${(p * 100).round()}%';

// Flood level of a community report: blues, to stay distinct from the risk colours.

const floodLevels = ['none', 'light', 'heavy'];

Color floodColor(String level) => switch (level) {
  'none' => const Color(0xFF2E9E5B),
  'light' => const Color(0xFF1E88E5),
  _ => const Color(0xFF283593),
};

IconData floodIcon(String level) => switch (level) {
  'none' => Icons.check_circle_outline,
  'light' => Icons.water_drop_outlined,
  _ => Icons.flood,
};

String floodLabel(String level) => switch (level) {
  'none' => 'Không ngập',
  'light' => 'Ngập nhẹ',
  _ => 'Ngập nặng',
};

String floodHint(String level) => switch (level) {
  'none' => 'Đường khô ráo',
  'light' => 'Tới mắt cá chân',
  _ => 'Tới bánh xe trở lên',
};

String statusLabel(String status) => switch (status) {
  'new' => 'Chờ xác minh',
  'verified' => 'Đã xác minh',
  'expired' => 'Hết hạn',
  _ => 'Bị từ chối',
};

String ago(int minutes) {
  if (minutes < 1) return 'Vừa xong';
  if (minutes < 60) return '$minutes phút trước';
  if (minutes < 1440) return '${minutes ~/ 60} giờ trước';
  return '${minutes ~/ 1440} ngày trước';
}
