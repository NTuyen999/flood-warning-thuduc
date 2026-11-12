import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import 'risk_colors.dart';

/// Loading / error-with-retry / data, for one request.
class LoadView<T> extends StatelessWidget {
  final Future<T> future;
  final VoidCallback onRetry;
  final Widget Function(BuildContext, T) builder;

  const LoadView({super.key, required this.future, required this.onRetry, required this.builder});

  @override
  Widget build(BuildContext context) => FutureBuilder<T>(
        future: future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) return ErrorRetry('${snap.error}', onRetry);
          return builder(context, snap.data as T);
        },
      );
}

class ErrorRetry extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const ErrorRetry(this.message, this.onRetry, {super.key});

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.cloud_off, size: 56, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton.tonalIcon(
                onPressed: onRetry, icon: const Icon(Icons.refresh), label: const Text('Thử lại')),
          ]),
        ),
      );
}

class EmptyState extends StatelessWidget {
  final IconData icon;
  final String message;

  const EmptyState(this.icon, this.message, {super.key});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 56, color: Theme.of(context).colorScheme.outline),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center),
        ]),
      );
}

/// Pill with icon + text, tinted with [color].
class Pill extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;

  const Pill(this.icon, this.label, this.color, {super.key});

  Pill.risk(String? level, {super.key})
      : icon = riskIcon(level),
        label = riskLabel(level),
        color = riskColor(level);

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.16),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 4),
          Text(label, style: Theme.of(context).textTheme.labelMedium),
        ]),
      );
}

class SectionTitle extends StatelessWidget {
  final String text;

  const SectionTitle(this.text, {super.key});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 8),
        child: Text(text, style: Theme.of(context).textTheme.titleMedium),
      );
}

/// flutter_map with the OpenStreetMap basemap (colours inverted in dark mode) and its attribution.
class BaseMap extends StatelessWidget {
  /// Tests turn tiles off: `flutter test` has no network.
  static bool tiles = true;

  final MapOptions options;
  final MapController? controller;
  final List<Widget> children;

  const BaseMap({super.key, required this.options, this.controller, this.children = const []});

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return FlutterMap(mapController: controller, options: options, children: [
      if (tiles)
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.example.mobile',
          tileBuilder: dark ? darkModeTileBuilder : null,
        ),
      ...children,
      // Own widget: flutter_map's SimpleAttributionWidget overflows on narrow maps.
      Align(
        alignment: Alignment.bottomLeft,
        child: ColoredBox(
          color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.7),
          child: const Padding(
            padding: EdgeInsets.symmetric(horizontal: 4, vertical: 1),
            child: Text('© OpenStreetMap contributors',
                style: TextStyle(fontSize: 10), overflow: TextOverflow.ellipsis),
          ),
        ),
      ),
    ]);
  }
}

/// TP Thu Duc bounding box, same as the backend's report validation.
bool inThuDuc(LatLng p) =>
    p.latitude >= 10.70 && p.latitude <= 10.93 && p.longitude >= 106.68 && p.longitude <= 106.90;

const thuDucCenter = LatLng(10.82, 106.77);

/// Device position, or null when location is off, denied or unavailable.
Future<LatLng?> currentLocation() async {
  try {
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
      return null;
    }
    final p = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(timeLimit: Duration(seconds: 8)));
    return LatLng(p.latitude, p.longitude);
  } catch (_) {
    return null; // no GPS fix, service off, or no plugin (tests)
  }
}
