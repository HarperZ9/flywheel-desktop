"""G1S tests for the canonical Flywheel Desktop release contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packaging" / "release-manifest.json"
SCHEMA = ROOT / "packaging" / "release-manifest.schema.json"
VALIDATOR = ROOT / "scripts" / "validate_release_manifest.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
BOUND_FIXTURE = FIXTURES / "release-manifest-bound-valid.json"
PAYLOAD_FIXTURE = FIXTURES / "payload-paths-valid.json"
class ReleaseContractTests(unittest.TestCase):
    maxDiff = None
    def _load_bound(self) -> dict[str, object]:
        return json.loads(BOUND_FIXTURE.read_text(encoding="utf-8"))

    def _run_validator(
        self,
        manifest: Path,
        *,
        payload_list: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.assertTrue(VALIDATOR.is_file(), "release contract validator is not implemented")
        command = [sys.executable, str(VALIDATOR), "--manifest", str(manifest)]
        if payload_list is not None:
            command.extend(["--payload-list", str(payload_list)])
        return subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    def _write_json(self, root: Path, name: str, payload: object) -> Path:
        path = root / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path
    def _assert_valid(self, manifest: Path, *, payload_list: Path | None = None) -> None:
        completed = self._run_validator(manifest, payload_list=payload_list)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(receipt["result"], "PASS")
        self.assertEqual(receipt["schema_version"], 1)
    def _assert_invalid(
        self,
        manifest: Path,
        *,
        payload_list: Path | None = None,
    ) -> dict[str, object]:
        completed = self._run_validator(manifest, payload_list=payload_list)
        self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        lines = [line for line in completed.stderr.splitlines() if line.strip()]
        self.assertTrue(lines, "validator failure did not emit a receipt")
        receipt = json.loads(lines[-1])
        self.assertEqual(receipt["result"], "FAIL")
        self.assertIsInstance(receipt["error"], str)
        self.assertTrue(receipt["error"])
        return receipt
    def test_canonical_pending_manifest_and_schema_validate(self) -> None:
        self.assertTrue(MANIFEST.is_file(), "canonical release manifest is missing")
        self.assertTrue(SCHEMA.is_file(), "release manifest schema is missing")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["title"], "Flywheel Desktop release manifest")
        self.assertFalse(schema["additionalProperties"])
        self._assert_valid(MANIFEST)
    def test_syntactically_bound_fixture_validates(self) -> None:
        self._assert_valid(BOUND_FIXTURE)
        self._assert_valid(BOUND_FIXTURE, payload_list=PAYLOAD_FIXTURE)
    def test_valid_allowlisted_payload_paths_validate(self) -> None:
        self._assert_valid(MANIFEST, payload_list=PAYLOAD_FIXTURE)

    def test_unknown_manifest_keys_fail_closed(self) -> None:
        cases = [
            ("root", ()),
            ("product", ("product",)),
            ("gateway", ("gateway",)),
            ("engine layout", ("engine_layout",)),
            ("installer", ("installer",)),
            ("release state", ("release_state",)),
            ("artifacts", ("artifacts",)),
            ("toolchain", ("toolchain",)),
            ("engine identity", ("engine_identity",)),
            ("engine builder", ("engine_identity", "builder")),
            ("payload policy", ("payload_policy",)),
            ("forbidden policy", ("payload_policy", "forbidden")),
            ("permitted root", ("payload_policy", "permitted_roots", 0)),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, path in cases:
                with self.subTest(label=label):
                    candidate = self._load_bound()
                    target = candidate
                    for part in path:
                        target = target[part]
                    target["unexpected"] = True
                    manifest = self._write_json(root, f"unknown-{label.replace(' ', '-')}.json", candidate)
                    self._assert_invalid(manifest)
    def test_malformed_bound_engine_identity_fails(self) -> None:
        cases = {
            "short commit": ("source_commit", "a" * 39),
            "non-hex commit": ("source_commit", "z" * 40),
            "newline commit": ("source_commit", "a" * 40 + "\n"),
            "uppercase commit": ("source_commit", "A" * 40),
            "short executable hash": ("executable_sha256", "a" * 63),
            "non-hex executable hash": ("executable_sha256", "z" * 64),
            "short runtime hash": ("runtime_manifest_sha256", "b" * 63),
            "non-hex runtime hash": ("runtime_manifest_sha256", "z" * 64),
            "newline runtime hash": ("runtime_manifest_sha256", "b" * 64 + "\n"),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, (field, value) in cases.items():
                with self.subTest(label=label):
                    candidate = self._load_bound()
                    candidate["engine_identity"][field] = value  # type: ignore[index]
                    manifest = self._write_json(root, f"malformed-{field}.json", candidate)
                    self._assert_invalid(manifest)
            for field in ("source_commit", "executable_sha256", "runtime_manifest_sha256", "builder"):
                candidate = self._load_bound()
                del candidate["engine_identity"][field]  # type: ignore[index]
                self._assert_invalid(self._write_json(root, f"missing-{field}.json", candidate))

    def test_pending_and_bound_states_cannot_be_mixed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bound = self._load_bound()
            pending = json.loads(MANIFEST.read_text(encoding="utf-8"))
            cases = [
                ("pending with bound identity", "engine-identity-pending", bound["engine_identity"]),
                ("bound with pending identity", "engine-bound-final", pending["engine_identity"]),
                ("unknown manifest state", "unknown", bound["engine_identity"]),
            ]
            for label, state, identity in cases:
                candidate = self._load_bound()
                candidate["manifest_state"], candidate["engine_identity"] = state, identity
                self._assert_invalid(self._write_json(root, f"state-{label}.json", candidate))
    def test_schema_versions_require_a_json_integer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, version in (("boolean", True), ("float", 1.0)):
                candidate = self._load_bound()
                candidate["schema_version"] = version
                self._assert_invalid(self._write_json(root, f"{label}-manifest-version.json", candidate))
                payload = {"schema_version": version, "paths": ["FlywheelDesktop.exe"]}
                self._assert_invalid(MANIFEST, payload_list=self._write_json(root, f"{label}-payload-version.json", payload))
    def test_pinned_contract_mismatches_fail(self) -> None:
        cases = {
            "product name": (("product", "name"), "Other"),
            "product version": (("product", "version"), "1.0.1"),
            "desktop build": (("product", "desktop_build_version"), "1.0.0+2"),
            "publisher": (("product", "publisher"), "Other Labs"),
            "desktop executable": (("product", "desktop_executable"), "Other.exe"),
            "gateway protocol": (("gateway", "protocol"), "flywheel.gateway/2"),
            "engine executable": (("engine_layout", "executable"), "engine/flywheel.exe"),
            "engine runtime": (("engine_layout", "runtime_root"), "runtime"),
            "installer AppId": (("installer", "app_id"), "{00000000-0000-0000-0000-000000000000}"),
            "channel": (("channel",), "public"),
            "signature": (("release_state", "signature"), "signed"),
            "redistribution": (("release_state", "redistribution"), "redistributable"),
            "portable artifact": (("artifacts", "portable"), "Flywheel-1.0.1-rc.1-internal-unsigned-nonredistributable-win64.zip"),
            "installer artifact": (("artifacts", "installer"), "Flywheel-1.0.1-rc.1-internal-unsigned-nonredistributable-Setup.exe"),
            "payload default": (("payload_policy", "default"), "accept"),
            "Python": (("toolchain", "python"), "3.13.0"),
            "PyInstaller": (("toolchain", "pyinstaller"), "6.20.0"),
            "Flutter": (("toolchain", "flutter"), "3.44.5"),
            "Dart": (("toolchain", "dart"), "3.12.1"),
            "Flutter commit": (("toolchain", "flutter_framework_commit"), "0" * 40),
            "Inno version": (("toolchain", "inno_setup"), "6.7.2"),
            "Inno hash": (("toolchain", "inno_setup_iscc_sha256"), "0" * 64),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source in (MANIFEST, BOUND_FIXTURE):
                for label, (path, value) in cases.items():
                    candidate = json.loads(source.read_text(encoding="utf-8"))
                    target = candidate
                    for part in path[:-1]:
                        target = target[part]
                    target[path[-1]] = value
                    with self.subTest(state=candidate["manifest_state"], label=label):
                        manifest = self._write_json(root, f"mismatch-{candidate['manifest_state']}-{label.replace(' ', '-')}.json", candidate)
                        self._assert_invalid(manifest)
    def test_artifact_names_carry_all_internal_boundary_labels(self) -> None:
        self.assertTrue(MANIFEST.is_file(), "canonical release manifest is missing")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for artifact in manifest["artifacts"].values():
            folded = artifact.casefold()
            for label in ("internal", "unsigned", "nonredistributable"):
                with self.subTest(artifact=artifact, label=label):
                    self.assertIn(label, folded)
    def test_payload_path_policy_rejects_unsafe_inputs(self) -> None:
        unsafe = {
            "traversal": "data/../secrets.txt",
            "posix absolute": "/Windows/System32/evil.dll",
            "drive absolute": "C:/Windows/System32/evil.dll",
            "backslash": r"data\flutter_assets\AssetManifest.bin",
            "UNC": "//server/share/file.txt",
            "drive relative": "C:relative.txt",
            "alternate data stream": "data/config.json:stream",
            "reserved device": "data/CON",
            "reserved device extension": "data/con.txt",
            "trailing dot component": "data/foo./bar.txt",
            "trailing space component": "data/foo /bar.txt",
            "unlisted root": "tmp/output.txt",
            "allowlist prefix": "data_evil/output.txt",
            "file prefix": "FlywheelDesktop.exe.bak",
            "engine executable sibling": "engine/bin/extra-tool.exe",
            "environment": "data/flutter_assets/.ENV.production",
            "private key": "engine/runtime/release.PEM",
            "PuTTY key": "engine/runtime/private.ppk",
            "credential file": "engine/runtime/credentials.json",
            "legacy private key": "engine/runtime/id_ecdsa",
            "OpenSSH security key": "engine/runtime/id_ed25519_sk",
            "private key backup": "engine/runtime/id_rsa.bak",
            "Java key store": "engine/runtime/keystore.jks",
            "signing key": "engine/runtime/signing-key.bin",
            "model": "engine/runtime/models/weights.gguf",
            "model filename": "engine/runtime/model.tflite",
            "model extension": "data/blob.GGUF",
            "weight filename": "data/weights.bin",
            "adapter weight": "engine/runtime/adapter.bin",
            "singular model binary": "engine/runtime/model/weights.bin",
            "checkpoint": "engine/runtime/checkpoints/epoch-1.ckpt",
            "checkpoint filename": "engine/runtime/checkpoint.bin",
            "checkpoint extension": "data/epoch.CKPT",
            "training data": "engine/runtime/training/dataset.json",
            "training filename": "engine/runtime/training.json",
            "train filename": "data/train.json",
            "dataset filename": "engine/runtime/dataset.json",
            "JSONL corpus": "engine/runtime/tasks/curated/corpus.jsonl",
            "GRPO": "engine/runtime/tasks/grpo-proof/receipt.json",
            "GRPO filename": "engine/runtime/grpo-proof.json",
            "git metadata": "engine/runtime/.git/config",
            "git metadata file": "engine/runtime/.gitmodules",
            "cache": "engine/runtime/__pycache__/module.pyc",
            "cache file": "engine/runtime/cache.db",
            "log": "engine/runtime/logs/gateway.log",
            "rotated log": "engine/runtime/gateway.log.1",
            "stdout log": "engine/runtime/gateway.out",
            "readiness": "engine/runtime/readiness/probe.json",
            "readiness file": "engine/runtime/readiness.txt",
            "ready file": "engine/runtime/ready.json",
            "research": "engine/runtime/research/notes.json",
            "research file": "engine/runtime/research-notes.txt",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for manifest in (MANIFEST, BOUND_FIXTURE):
                for label, path in unsafe.items():
                    payload = {"schema_version": 1, "paths": ["FlywheelDesktop.exe", path]}
                    payload_list = self._write_json(root, f"unsafe-{manifest.stem}-{label.replace(' ', '-')}.json", payload)
                    with self.subTest(state=manifest.name, label=label, path=path):
                        self._assert_invalid(manifest, payload_list=payload_list)
    def test_duplicate_json_object_keys_fail_at_every_input_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = MANIFEST.read_text(encoding="utf-8")
            root_dup = root / "root-duplicate.json"
            root_dup.write_text(canonical.replace('"schema_version": 1,', '"schema_version": 1,\n  "schema_version": 1,', 1), encoding="utf-8")
            nested_dup = root / "nested-duplicate.json"
            nested_dup.write_text(canonical.replace('"state": "pending",', '"state": "pending",\n    "state": "pending",', 1), encoding="utf-8")
            payload_dup = root / "payload-duplicate.json"
            payload_dup.write_text('{"schema_version":1,"paths":["FlywheelDesktop.exe"],"paths":[]}', encoding="utf-8")
            for path, payload in ((root_dup, None), (nested_dup, None), (MANIFEST, payload_dup)):
                receipt = self._assert_invalid(path, payload_list=payload)
                self.assertIn("duplicate", receipt["error"].casefold())
    def test_payload_path_list_rejects_casefold_duplicates_and_unknown_keys(self) -> None:
        cases = {
            "casefold duplicate": {
                "schema_version": 1,
                "paths": ["FlywheelDesktop.exe", "flywheeldesktop.exe"],
            },
            "unknown key": {
                "schema_version": 1,
                "paths": ["FlywheelDesktop.exe"],
                "ignored": True,
            },
            "Win32 trailing-dot collision": {
                "schema_version": 1,
                "paths": ["data/foo/bar.txt", "data/foo./bar.txt"],
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, payload in cases.items():
                with self.subTest(label=label):
                    payload_list = self._write_json(root, f"payload-{label.replace(' ', '-')}.json", payload)
                    self._assert_invalid(MANIFEST, payload_list=payload_list)
if __name__ == "__main__":
    unittest.main()
