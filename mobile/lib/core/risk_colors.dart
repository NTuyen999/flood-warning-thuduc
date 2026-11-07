import 'package:flutter/material.dart';

Color riskColor(String level) => switch (level) {
  'green' => Colors.green,
  'yellow' => Colors.amber,
  'orange' => Colors.orange,
  'red' => Colors.red,
  _ => Colors.grey,
};

const riskOrder = ['green', 'yellow', 'orange', 'red'];

String riskLabel(String level) => switch (level) {
  'green' => 'Thấp',
  'yellow' => 'Trung bình',
  'orange' => 'Cao',
  'red' => 'Rất cao',
  _ => 'Không rõ',
};