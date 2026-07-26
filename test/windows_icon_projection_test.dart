import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flywheel_desktop/theme/tokens.dart';
import 'package:flywheel_desktop/widgets/aperture.dart';

const _apertureSource = 'lib/widgets/aperture.dart';
const _apertureSourceSha256 =
    '83d226c452da4c401874ce5891dab75803846141c08381b44b1cd73a29904a30';
const _iconPath = 'windows/runner/resources/app_icon.ico';
const _requiredSizes = <int>[16, 32, 48, 256];
const _stockFlutterIconSha256 =
    'c098d3fc85cacff98b8e69811b48e9f0d852fcee278132d794411d978869cbf8';
const _updateTrackedIcon = bool.fromEnvironment('UPDATE_WINDOWS_ICON');

void main() {
  testWidgets('the tracked Windows icon is a byte-stable Aperture projection',
      (tester) async {
    final sourceHash = sha256.convert(File(_apertureSource).readAsBytesSync());
    expect(sourceHash.toString(), _apertureSourceSha256);

    final first = await _projectApertureIcon(tester);
    final second = await _projectApertureIcon(tester);

    expect(second, orderedEquals(first),
        reason: 'two consecutive projections must be byte-identical');
    expect(_readIcoSizes(first), orderedEquals(_requiredSizes));
    expect(sha256.convert(first).toString(), isNot(_stockFlutterIconSha256));

    final trackedIcon = File(_iconPath);
    if (_updateTrackedIcon) {
      trackedIcon.writeAsBytesSync(first, flush: true);
    }
    expect(trackedIcon.readAsBytesSync(), orderedEquals(first),
        reason: 'regenerate with --dart-define=UPDATE_WINDOWS_ICON=true');
  });
}

Future<Uint8List> _projectApertureIcon(WidgetTester tester) async {
  final frames = <MapEntry<int, Uint8List>>[];
  for (final size in _requiredSizes) {
    frames.add(MapEntry(size, await _renderApertureFrame(tester, size)));
  }
  return _encodeIco(frames);
}

Future<Uint8List> _renderApertureFrame(WidgetTester tester, int size) async {
  final boundaryKey = GlobalKey();
  await tester.pumpWidget(
    Directionality(
      textDirection: TextDirection.ltr,
      child: Align(
        alignment: Alignment.topLeft,
        child: Theme(
          data: ThemeData(extensions: const [FwTokens.light]),
          child: RepaintBoundary(
            key: boundaryKey,
            child: ColoredBox(
              color: FwTokens.light.ground,
              child: SizedBox.square(
                dimension: size.toDouble(),
                child: ApertureMark(size: size.toDouble()),
              ),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pump();

  final boundary =
      boundaryKey.currentContext!.findRenderObject()! as RenderRepaintBoundary;
  expect(boundary.size, Size.square(size.toDouble()));
  final bytes = await tester.binding.runAsync<Uint8List>(() async {
    final image = await boundary.toImage(pixelRatio: 1);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose();
    expect(data, isNotNull);
    return data!.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
  });
  expect(bytes, isNotNull);
  return bytes!;
}

Uint8List _encodeIco(List<MapEntry<int, Uint8List>> frames) {
  const directoryHeaderSize = 6;
  const directoryEntrySize = 16;
  final directory =
      ByteData(directoryHeaderSize + directoryEntrySize * frames.length);
  directory.setUint16(0, 0, Endian.little);
  directory.setUint16(2, 1, Endian.little);
  directory.setUint16(4, frames.length, Endian.little);

  var imageOffset = directory.lengthInBytes;
  for (var index = 0; index < frames.length; index++) {
    final frame = frames[index];
    final entryOffset = directoryHeaderSize + directoryEntrySize * index;
    directory.setUint8(entryOffset, frame.key == 256 ? 0 : frame.key);
    directory.setUint8(entryOffset + 1, frame.key == 256 ? 0 : frame.key);
    directory.setUint8(entryOffset + 2, 0);
    directory.setUint8(entryOffset + 3, 0);
    directory.setUint16(entryOffset + 4, 1, Endian.little);
    directory.setUint16(entryOffset + 6, 32, Endian.little);
    directory.setUint32(entryOffset + 8, frame.value.length, Endian.little);
    directory.setUint32(entryOffset + 12, imageOffset, Endian.little);
    imageOffset += frame.value.length;
  }

  final output = BytesBuilder(copy: false)..add(directory.buffer.asUint8List());
  for (final frame in frames) {
    output.add(frame.value);
  }
  return output.takeBytes();
}

List<int> _readIcoSizes(Uint8List icon) {
  const pngSignature = <int>[137, 80, 78, 71, 13, 10, 26, 10];
  final data = ByteData.sublistView(icon);
  expect(data.getUint16(0, Endian.little), 0);
  expect(data.getUint16(2, Endian.little), 1);
  final count = data.getUint16(4, Endian.little);
  final sizes = <int>[];

  for (var index = 0; index < count; index++) {
    final entryOffset = 6 + 16 * index;
    final encodedWidth = data.getUint8(entryOffset);
    final encodedHeight = data.getUint8(entryOffset + 1);
    final width = encodedWidth == 0 ? 256 : encodedWidth;
    final height = encodedHeight == 0 ? 256 : encodedHeight;
    expect(height, width);
    expect(data.getUint16(entryOffset + 4, Endian.little), 1);
    expect(data.getUint16(entryOffset + 6, Endian.little), 32);

    final length = data.getUint32(entryOffset + 8, Endian.little);
    final offset = data.getUint32(entryOffset + 12, Endian.little);
    expect(offset + length, lessThanOrEqualTo(icon.length));
    expect(icon.sublist(offset, offset + pngSignature.length),
        orderedEquals(pngSignature));
    expect(icon.sublist(offset + 12, offset + 16),
        orderedEquals(const <int>[73, 72, 68, 82]));
    expect(data.getUint32(offset + 16, Endian.big), width);
    expect(data.getUint32(offset + 20, Endian.big), height);
    sizes.add(width);
  }
  return sizes;
}
