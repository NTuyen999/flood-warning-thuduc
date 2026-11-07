import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';

void main() {
  testWidgets('App khởi động được', (tester) async {
    await tester.pumpWidget(const FloodApp());
    expect(find.text('Bản đồ nguy cơ'), findsOneWidget);
  });
}