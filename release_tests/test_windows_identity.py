"""G5M tests for manifest-to-Windows identity convergence."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import verify_windows_identity as identity_checker


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packaging" / "release-manifest.json"
CHECKER = ROOT / "scripts" / "verify_windows_identity.py"
RELEASE_PE = ROOT / "build" / "windows" / "x64" / "runner" / "Release" / "FlywheelDesktop.exe"


class WindowsIdentityConvergenceTests(unittest.TestCase):
    maxDiff = None

    def _run_checker(
        self, manifest: Path, *, pe: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        self.assertTrue(CHECKER.is_file(), "Windows identity checker is not implemented")
        command = [sys.executable, str(CHECKER), "--manifest", str(manifest)]
        if pe is not None:
            command.extend(["--pe", str(pe)])
        return subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_native_identity_matches_the_read_only_manifest(self) -> None:
        before = MANIFEST.read_bytes()
        completed = self._run_checker(MANIFEST)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(receipt["result"], "PASS")
        self.assertEqual(
            receipt["identity"],
            {
                "channel": "internal-rc.1",
                "desktop_build_version": "1.0.0+1",
                "desktop_executable": "FlywheelDesktop.exe",
                "file_description": "Flywheel (internal release candidate, unsigned)",
                "prerelease": "yes",
                "publisher": "Zentropy Labs",
                "product_name": "Flywheel",
                "product_version": "1.0.0",
                "redistribution": "blocked-license-unset",
                "signature": "unsigned",
                "special_build": "internal-rc.1, unsigned, not for redistribution",
                "windows_version": "1.0.0.1",
            },
        )
        self.assertEqual(MANIFEST.read_bytes(), before, "checker modified its manifest input")

    def test_product_and_build_version_mismatches_fail_without_writes(self) -> None:
        canonical = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cases = {
            "product version": ("version", "1.0.1"),
            "desktop build number": ("desktop_build_version", "1.0.0+2"),
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, (field, value) in cases.items():
                with self.subTest(label=label):
                    candidate = json.loads(json.dumps(canonical))
                    candidate["product"][field] = value
                    manifest = root / f"mismatch-{field}.json"
                    manifest.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
                    before = manifest.read_bytes()

                    completed = self._run_checker(manifest)

                    self.assertNotEqual(
                        completed.returncode,
                        0,
                        "deliberate manifest/native mismatch unexpectedly passed",
                    )
                    lines = [line for line in completed.stderr.splitlines() if line.strip()]
                    self.assertTrue(lines, "checker failure did not emit a receipt")
                    receipt = json.loads(lines[-1])
                    self.assertEqual(receipt["result"], "FAIL")
                    self.assertIn("mismatch", receipt["error"].casefold())
                    self.assertEqual(
                        manifest.read_bytes(),
                        before,
                        "checker modified its manifest input",
                    )

    def test_corrupted_or_ambiguous_versioninfo_entries_fail_closed(self) -> None:
        source = (ROOT / "windows" / "runner" / "Runner.rc").read_text(
            encoding="utf-8"
        )
        cases = {
            "file version directive": (
                " FILEVERSION VERSION_AS_NUMBER",
                " FILEVERSION 9,9,9,9",
            ),
            "product version directive": (
                " PRODUCTVERSION VERSION_AS_NUMBER",
                " PRODUCTVERSION 9,9,9,9",
            ),
            "file version value": (
                '            VALUE "FileVersion", VERSION_AS_STRING "\\0"',
                '            VALUE "FileVersion", "9.9.9.9" "\\0"',
            ),
            "product version value": (
                '            VALUE "ProductVersion", VERSION_AS_STRING "\\0"',
                '            VALUE "ProductVersion", "9.9.9.9" "\\0"',
            ),
            "missing file version value": (
                '            VALUE "FileVersion", VERSION_AS_STRING "\\0"\n',
                "",
            ),
            "duplicate product version value": (
                '            VALUE "ProductVersion", VERSION_AS_STRING "\\0"',
                '            VALUE "ProductVersion", VERSION_AS_STRING "\\0"\n'
                '            VALUE "ProductVersion", VERSION_AS_STRING "\\0"',
            ),
        }
        identity = identity_checker._manifest_identity(
            identity_checker._read_manifest(MANIFEST)
        )

        with tempfile.TemporaryDirectory() as directory:
            runner_rc = Path(directory) / "Runner.rc"
            for label, (old, new) in cases.items():
                with self.subTest(label=label):
                    self.assertEqual(source.count(old), 1, f"fixture anchor drifted: {old}")
                    runner_rc.write_text(source.replace(old, new), encoding="utf-8")
                    with mock.patch.object(identity_checker, "RUNNER_RC", runner_rc):
                        with self.assertRaises(identity_checker.IdentityError):
                            identity_checker._verify_sources(identity)

    @unittest.skipUnless(RELEASE_PE.is_file(), "release Windows executable is not built")
    def test_built_release_pe_carries_the_manifest_identity(self) -> None:
        completed = self._run_checker(MANIFEST, pe=RELEASE_PE)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(receipt["result"], "PASS")
        self.assertEqual(
            receipt["pe"],
            {
                "CompanyName": "Zentropy Labs",
                "FileDescription": "Flywheel (internal release candidate, unsigned)",
                # 0x22 = VS_FF_PRERELEASE | VS_FF_SPECIALBUILD. An unsigned
                # internal build must say so on the file itself, because the
                # file travels without the manifest that describes it.
                "FileFlags": 0x22,
                "FileVersion": "1.0.0.1",
                "FileVersionFixed": "1.0.0.1",
                "InternalName": "FlywheelDesktop",
                "OriginalFilename": "FlywheelDesktop.exe",
                "ProductName": "Flywheel",
                "ProductVersion": "1.0.0.1",
                "ProductVersionFixed": "1.0.0.1",
                "SpecialBuild": "internal-rc.1, unsigned, not for redistribution",
            },
        )

    def test_pe_verifier_rejects_filename_and_version_metadata_mismatches(self) -> None:
        identity = identity_checker._manifest_identity(
            identity_checker._read_manifest(MANIFEST)
        )
        valid = {
            "CompanyName": "Zentropy Labs",
            "FileDescription": "Flywheel",
            "FileVersion": "1.0.0.1",
            "FileVersionFixed": "1.0.0.1",
            "InternalName": "FlywheelDesktop",
            "OriginalFilename": "FlywheelDesktop.exe",
            "ProductName": "Flywheel",
            "ProductVersion": "1.0.0.1",
            "ProductVersionFixed": "1.0.0.1",
        }
        cases = {
            "filename": (Path("Other.exe"), None),
            "fixed file version": (
                Path("FlywheelDesktop.exe"),
                ("FileVersionFixed", "9.9.9.9"),
            ),
            "string file version": (
                Path("FlywheelDesktop.exe"),
                ("FileVersion", "9.9.9.9"),
            ),
            "fixed product version": (
                Path("FlywheelDesktop.exe"),
                ("ProductVersionFixed", "9.9.9.9"),
            ),
            "string product version": (
                Path("FlywheelDesktop.exe"),
                ("ProductVersion", "9.9.9.9"),
            ),
        }
        for label, (path, mutation) in cases.items():
            with self.subTest(label=label):
                values = dict(valid)
                if mutation is not None:
                    values[mutation[0]] = mutation[1]
                with mock.patch.object(
                    identity_checker, "_read_pe_identity", return_value=values
                ):
                    with self.assertRaises(identity_checker.IdentityError):
                        identity_checker._verify_pe(path, identity)


if __name__ == "__main__":
    unittest.main()
