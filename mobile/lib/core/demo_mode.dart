import 'package:flutter/foundation.dart';

class DemoState {
  final bool enabled;
  final String scenario;

  const DemoState({this.enabled = false, this.scenario = 'heavy'});

  DemoState copyWith({bool? enabled, String? scenario}) {
    return DemoState(
      enabled: enabled ?? this.enabled,
      scenario: scenario ?? this.scenario,
    );
  }
}

class DemoModeNotifier extends ValueNotifier<DemoState> {
  DemoModeNotifier() : super(const DemoState());

  void setEnabled(bool enabled) {
    value = value.copyWith(enabled: enabled);
  }

  void setScenario(String scenario) {
    value = value.copyWith(scenario: scenario);
  }

  void toggle() {
    value = value.copyWith(enabled: !value.enabled);
  }
}

/// Global demo mode notifier for the application.
final demoMode = DemoModeNotifier();
