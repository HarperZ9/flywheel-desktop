// auth_client.dart: attach the gateway bearer token to every request.
//
// The gateway requires a bearer token, a loopback Host, and a JSON content type
// on state-changing methods. Rather than edit 42 call sites in gateway_client
// and gateway_streams, this wraps the inner http.Client: every request the typed
// client makes, including the two SSE streams, passes through send() here.
//
// The token is a local file the gateway wrote with owner-only permissions. This
// app reads it, sends it as a header, and does nothing else with it: never
// displayed, never logged, never placed in a URL or a query string.
//
// A missing token file is a legitimate state, not an error. An older gateway
// does not require one, so readGatewayToken returns null and the client sends
// no header at all rather than an empty bearer.

import 'dart:io';

import 'package:http/http.dart' as http;

const String tokenFilename = 'gateway.token';

/// Read the gateway token from FLYWHEEL_HOME, defaulting to ~/.flywheel.
///
/// Returns null when the file is absent, unreadable, or blank. Degrading rather
/// than throwing matters here: the app must still start and still show an honest
/// offline state when the engine has never been run.
String? readGatewayToken({String? homeOverride}) {
  try {
    final env = Platform.environment;
    final profile = env['USERPROFILE'] ?? env['HOME'] ?? '';
    final home = homeOverride ??
        env['FLYWHEEL_HOME'] ??
        '$profile${Platform.pathSeparator}.flywheel';
    final f = File('$home${Platform.pathSeparator}$tokenFilename');
    if (!f.existsSync()) return null;
    final t = f.readAsStringSync().trim();
    return t.isEmpty ? null : t;
  } catch (_) {
    return null;
  }
}

/// An http.Client that adds the bearer header to every outbound request.
class AuthClient extends http.BaseClient {
  final http.Client _inner;
  final String? _token;

  AuthClient(this._inner, this._token);

  /// True when a token was found. The UI may show that the connection is
  /// authenticated; it must never show the token itself.
  bool get hasToken => _token != null;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    final t = _token;
    if (t != null) {
      request.headers['Authorization'] = 'Bearer $t';
    }
    return _inner.send(request);
  }

  @override
  void close() => _inner.close();
}
