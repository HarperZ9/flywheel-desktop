import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:flywheel_desktop/client/auth_client.dart';

class _Recorder extends http.BaseClient {
  final List<Map<String, String>> seen = [];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    // package:http stores headers in a case-insensitive map. Copying it into a
    // plain Map would preserve the caller's casing and make lookups brittle, so
    // normalize to lowercase here.
    seen.add({
      for (final e in request.headers.entries) e.key.toLowerCase(): e.value,
    });
    return http.StreamedResponse(Stream.value(utf8.encode('{"ok":true}')), 200);
  }
}

void main() {
  test('a token is sent as a bearer header on every request', () async {
    final rec = _Recorder();
    final client = AuthClient(rec, 'tok-abc');
    await client.get(Uri.parse('http://127.0.0.1:8799/api/world'));
    await client.post(Uri.parse('http://127.0.0.1:8799/api/companion'),
        headers: {'Content-Type': 'application/json'}, body: '{}');
    expect(rec.seen.length, 2);
    for (final h in rec.seen) {
      expect(h['authorization'], 'Bearer tok-abc');
    }
  });

  test('a null token sends no authorization header at all', () async {
    final rec = _Recorder();
    await AuthClient(rec, null)
        .get(Uri.parse('http://127.0.0.1:8799/api/world'));
    final h = rec.seen.single;
    expect(h.containsKey('authorization'), isFalse);
  });

  test('an existing content type is preserved', () async {
    final rec = _Recorder();
    await AuthClient(rec, 'tok').post(
        Uri.parse('http://127.0.0.1:8799/api/companion'),
        headers: {'Content-Type': 'application/json'},
        body: '{}');
    expect(rec.seen.single['content-type'], contains('application/json'));
  });

  test('a missing token file yields null rather than throwing', () {
    expect(readGatewayToken(homeOverride: 'Z:/definitely/not/a/real/path'),
        isNull);
  });

  test('a token file that exists is read and trimmed', () {
    // Written into the test temp dir so the real ~/.flywheel is never touched.
    final dir = Directory.systemTemp.createTempSync('fwtok');
    File('${dir.path}/$tokenFilename').writeAsStringSync('  abc123\n');
    expect(readGatewayToken(homeOverride: dir.path), 'abc123');
    dir.deleteSync(recursive: true);
  });

  test('an empty token file reads as null, not as an empty bearer', () {
    final dir = Directory.systemTemp.createTempSync('fwtok');
    File('${dir.path}/$tokenFilename').writeAsStringSync('   \n');
    expect(readGatewayToken(homeOverride: dir.path), isNull);
    dir.deleteSync(recursive: true);
  });
}
