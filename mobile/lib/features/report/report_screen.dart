import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:image_picker/image_picker.dart';
import 'package:latlong2/latlong.dart';

import '../../core/risk_colors.dart';
import '../../core/widgets.dart';
import '../../data/models/road_segment.dart';
import '../../data/services/api.dart';
import '../../data/services/api_service.dart';

/// Community report form. Pops `true` once a report has been sent.
class ReportScreen extends StatefulWidget {
  /// Opened from a road segment: the pin starts on it.
  final RoadSegment? segment;

  const ReportScreen({super.key, this.segment});

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  final _map = MapController();
  final _note = TextEditingController();
  late LatLng _pin = widget.segment?.middle ?? thuDucCenter;
  String? _level;
  String? _photo;
  bool _sending = false;
  String? _locationHint;

  @override
  void initState() {
    super.initState();
    // From a segment the pin is already right; otherwise start at the user's position.
    if (widget.segment == null) _useMyLocation();
  }

  @override
  void dispose() {
    _map.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _useMyLocation() async {
    final here = await currentLocation();
    if (!mounted) return;
    if (here != null && inThuDuc(here)) {
      setState(() {
        _pin = here;
        _locationHint = null;
      });
      _map.move(here, 16);
    } else {
      setState(() => _locationHint = here == null
          ? 'Không lấy được vị trí. Chạm vào bản đồ để chọn nơi bạn quan sát.'
          : 'Bạn đang ở ngoài TP Thủ Đức. Chạm vào bản đồ để chọn nơi bạn quan sát.');
    }
  }

  Future<void> _pickPhoto(ImageSource source) async {
    try {
      // Resized + recompressed so the upload stays far below the server's 5 MB limit.
      final file = await ImagePicker().pickImage(source: source, maxWidth: 1600, imageQuality: 80);
      if (file != null && mounted) setState(() => _photo = file.path);
    } catch (_) {
      _say('Không mở được máy ảnh hoặc thư viện ảnh.');
    }
  }

  void _say(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _send() async {
    setState(() => _sending = true);
    try {
      await api.sendReport(
          at: _pin, floodLevel: _level!, note: _note.text.trim(), imagePath: _photo);
      _say('Đã gửi báo cáo. Cảm ơn bạn!');
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.status == 409) {
        // Someone already reported the same thing here: good news, not an error.
        setState(() => _sending = false);
        await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            icon: const Icon(Icons.groups),
            title: const Text('Đã có người báo cáo'),
            content: const Text(
                'Tình trạng này vừa được báo cáo ở gần đây nên không cần gửi lại. Cảm ơn bạn!'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: const Text('Đã hiểu')),
            ],
          ),
        );
        if (mounted) Navigator.pop(context, false);
      } else {
        _say(e.message);
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Báo cáo tình trạng đường')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        children: [
          const SectionTitle('1. Đường đang thế nào?'),
          Row(children: [
            for (final level in floodLevels)
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  child: _LevelCard(
                    level: level,
                    selected: _level == level,
                    onTap: () => setState(() => _level = level),
                  ),
                ),
              ),
          ]),
          const SectionTitle('2. Ở đâu?'),
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: SizedBox(
              height: 220,
              child: BaseMap(
                controller: _map,
                options: MapOptions(
                  initialCenter: _pin,
                  initialZoom: 16,
                  onTap: (_, point) => setState(() {
                    _pin = point;
                    _locationHint = null;
                  }),
                ),
                children: [
                  MarkerLayer(markers: [
                    Marker(
                      point: _pin,
                      width: 44,
                      height: 44,
                      alignment: Alignment.topCenter,
                      child: Icon(Icons.location_on, size: 44, color: scheme.error),
                    ),
                  ]),
                ],
              ),
            ),
          ),
          const SizedBox(height: 4),
          Row(children: [
            Expanded(
              child: Text(
                _locationHint ?? 'Chạm vào bản đồ để chỉnh vị trí ghim.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
            TextButton.icon(
              onPressed: _useMyLocation,
              icon: const Icon(Icons.my_location, size: 18),
              label: const Text('Vị trí của tôi'),
            ),
          ]),
          const SectionTitle('3. Ảnh và ghi chú (không bắt buộc)'),
          if (_photo == null)
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _pickPhoto(ImageSource.camera),
                  icon: const Icon(Icons.photo_camera),
                  label: const Text('Chụp ảnh'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _pickPhoto(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Chọn ảnh'),
                ),
              ),
            ])
          else
            Stack(alignment: Alignment.topRight, children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.file(File(_photo!),
                    height: 180, width: double.infinity, fit: BoxFit.cover),
              ),
              IconButton.filledTonal(
                tooltip: 'Bỏ ảnh',
                onPressed: () => setState(() => _photo = null),
                icon: const Icon(Icons.close),
              ),
            ]),
          const SizedBox(height: 12),
          TextField(
            controller: _note,
            maxLength: 500,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Ghi chú',
              hintText: 'Ví dụ: nước ngập tới nửa bánh xe máy',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: _level == null || _sending ? null : _send,
            icon: _sending
                ? const SizedBox(
                    width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.send),
            label: Text(_level == null ? 'Chọn tình trạng đường để gửi' : 'Gửi báo cáo'),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
          ),
        ],
      ),
    );
  }
}

class _LevelCard extends StatelessWidget {
  final String level;
  final bool selected;
  final VoidCallback onTap;

  const _LevelCard({required this.level, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final color = floodColor(level);
    return Semantics(
      button: true,
      selected: selected,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
          decoration: BoxDecoration(
            color: selected ? color.withValues(alpha: 0.16) : null,
            border: Border.all(
              color: selected ? color : Theme.of(context).colorScheme.outlineVariant,
              width: selected ? 2 : 1,
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(children: [
            Icon(floodIcon(level), size: 36, color: color),
            const SizedBox(height: 6),
            Text(floodLabel(level), style: Theme.of(context).textTheme.titleSmall),
            Text(floodHint(level),
                textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall),
          ]),
        ),
      ),
    );
  }
}
