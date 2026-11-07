import 'package:flutter/material.dart';

Color riskColor(String level) => switch (level) {
  'green' => Colors.green,
  'yellow' => Colors.amber,
  'orange' => Colors.orange,
  'red' => Colors.red,
  _ => Colors.grey,
};