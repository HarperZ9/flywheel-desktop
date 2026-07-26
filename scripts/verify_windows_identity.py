"""Verify Flywheel's manifest, Dart, native Windows, and optional PE identity."""

from __future__ import annotations

import argparse
import ctypes
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBSPEC = ROOT / "pubspec.yaml"
CMAKE = ROOT / "windows" / "CMakeLists.txt"
RUNNER_RC = ROOT / "windows" / "runner" / "Runner.rc"
MAIN_CPP = ROOT / "windows" / "runner" / "main.cpp"


class IdentityError(ValueError):
    """A projected identity surface does not match the release manifest."""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise IdentityError(f"could not read {path}: {exc}") from exc


def _read_manifest(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        raise IdentityError(f"could not parse manifest {path}: {exc}") from exc
    if not isinstance(value, Mapping) or not isinstance(value.get("product"), Mapping):
        raise IdentityError("manifest.product must be an object")
    return value


def _require_string(value: Mapping[str, Any], key: str, label: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise IdentityError(f"{label}.{key} must be a non-empty string")
    return item


def _capture(pattern: str, text: str, label: str) -> str:
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    if len(matches) != 1:
        raise IdentityError(f"expected exactly one {label}; found {len(matches)}")
    return matches[0]


def _expect(label: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise IdentityError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def _manifest_identity(manifest: Mapping[str, Any]) -> dict[str, str]:
    product = manifest["product"]
    assert isinstance(product, Mapping)
    name = _require_string(product, "name", "manifest.product")
    product_version = _require_string(product, "version", "manifest.product")
    build_version = _require_string(product, "desktop_build_version", "manifest.product")
    publisher = _require_string(product, "publisher", "manifest.product")
    executable = _require_string(product, "desktop_executable", "manifest.product")

    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)\+(\d+)", build_version)
    if match is None:
        raise IdentityError("manifest.product.desktop_build_version must be X.Y.Z+BUILD")
    base_version = ".".join(match.groups()[:3])
    _expect("manifest product/build version", product_version, base_version)
    if Path(executable).name != executable or not executable.casefold().endswith(".exe"):
        raise IdentityError("manifest.product.desktop_executable must be an .exe basename")

    # A manifest that says "internal-rc.1, unsigned" is worthless if the binary
    # it describes says only "Flywheel 1.0.0.1, Zentropy Labs". The file travels
    # without the manifest, so the disclosure has to be in the file.
    channel = _require_string(manifest, "channel", "manifest")
    release_state = manifest["release_state"]
    assert isinstance(release_state, Mapping)
    signature = _require_string(release_state, "signature", "manifest.release_state")
    redistribution = _require_string(
        release_state, "redistribution", "manifest.release_state"
    )
    prerelease = channel != "stable"
    special_build = (
        f"{channel}, {signature}, not for redistribution"
        if prerelease or signature != "signed"
        else ""
    )
    file_description = (
        f"{name} (internal release candidate, {signature})"
        if prerelease
        else name
    )

    return {
        "channel": channel,
        "desktop_build_version": build_version,
        "desktop_executable": executable,
        "file_description": file_description,
        "prerelease": "yes" if prerelease else "no",
        "publisher": publisher,
        "product_name": name,
        "product_version": product_version,
        "redistribution": redistribution,
        "signature": signature,
        "special_build": special_build,
        "windows_version": ".".join(match.groups()),
    }


def _verify_sources(identity: Mapping[str, str]) -> None:
    pubspec = _read_text(PUBSPEC)
    cmake = _read_text(CMAKE)
    runner_rc = _read_text(RUNNER_RC)
    main_cpp = _read_text(MAIN_CPP)

    pubspec_version = _capture(r"^version:\s*([^\s#]+)\s*$", pubspec, "pubspec version")
    _expect("pubspec version", pubspec_version, identity["desktop_build_version"])

    binary_name = _capture(
        r'^\s*set\(BINARY_NAME\s+"([^"]+)"\s*\)\s*$', cmake, "CMake BINARY_NAME"
    )
    executable_stem = Path(identity["desktop_executable"]).stem
    _expect("CMake executable name", binary_name, executable_stem)

    window_title = _capture(
        r'window\.Create\(L"([^"]+)"', main_cpp, "native window title"
    )
    _expect("native window title", window_title, identity["product_name"])

    numeric_version = _capture(
        r"^#define\s+VERSION_AS_NUMBER\s+([0-9, ]+)\s*$",
        runner_rc,
        "Runner.rc numeric version",
    ).replace(" ", "")
    _expect(
        "Runner.rc numeric version",
        numeric_version,
        identity["windows_version"].replace(".", ","),
    )
    string_version = _capture(
        r'^#define\s+VERSION_AS_STRING\s+"([^"]+)"\s*$',
        runner_rc,
        "Runner.rc string version",
    )
    _expect("Runner.rc string version", string_version, identity["windows_version"])
    for directive in ("FILEVERSION", "PRODUCTVERSION"):
        value = _capture(
            rf"^\s*{directive}\s+(\S+)\s*$",
            runner_rc,
            f"Runner.rc {directive} directive",
        )
        _expect(f"Runner.rc {directive} directive", value, "VERSION_AS_NUMBER")

    if identity["prerelease"] == "yes":
        # Every FILEFLAGS branch, debug and release alike. A debug build of a
        # prerelease is still a prerelease, and checking only one branch lets
        # the other drift into looking like a shipped build.
        branches = re.findall(r"^\s*FILEFLAGS\s+(.+?)\s*$", runner_rc, re.MULTILINE)
        if not branches:
            raise IdentityError("Runner.rc declares no FILEFLAGS")
        for flags in branches:
            for required in ("VS_FF_PRERELEASE", "VS_FF_SPECIALBUILD"):
                if required not in flags:
                    raise IdentityError(
                        f"Runner.rc FILEFLAGS {flags!r} must include {required}; "
                        f"manifest channel is {identity['channel']} and "
                        f"signature is {identity['signature']}"
                    )

    expected_fields = {
        "CompanyName": identity["publisher"],
        "FileDescription": identity["file_description"],
        "FileVersion": identity["windows_version"],
        "InternalName": executable_stem,
        "OriginalFilename": identity["desktop_executable"],
        "ProductName": identity["product_name"],
        "ProductVersion": identity["windows_version"],
    }
    if identity["special_build"]:
        expected_fields["SpecialBuild"] = identity["special_build"]
    for field, expected in expected_fields.items():
        if field in {"FileVersion", "ProductVersion"}:
            value_macro = _capture(
                rf'^\s*VALUE\s+"{field}",\s*(VERSION_AS_STRING)\s+"\\0"\s*$',
                runner_rc,
                f"Runner.rc {field}",
            )
            _expect(f"Runner.rc {field} value macro", value_macro, "VERSION_AS_STRING")
            actual = string_version
        else:
            actual = _capture(
                rf'^\s*VALUE\s+"{field}",\s*"([^"]+)"',
                runner_rc,
                f"Runner.rc {field}",
            )
        _expect(f"Runner.rc {field}", actual, expected)


class _VsFixedFileInfo(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in (
        "signature", "struct_version", "file_version_ms", "file_version_ls",
        "product_version_ms", "product_version_ls", "file_flags_mask",
        "file_flags", "file_os", "file_type", "file_subtype", "file_date_ms",
        "file_date_ls",
    )]


def _read_pe_identity(path: Path) -> dict[str, str]:
    if sys.platform != "win32":
        raise IdentityError("PE metadata verification requires Windows")
    if not path.is_file():
        raise IdentityError(f"PE executable does not exist: {path}")

    version = ctypes.WinDLL("version", use_last_error=True)
    handle = ctypes.c_uint32()
    size = version.GetFileVersionInfoSizeW(str(path), ctypes.byref(handle))
    if size == 0:
        raise IdentityError(f"PE has no readable VERSIONINFO: {path}")
    buffer = ctypes.create_string_buffer(size)
    if not version.GetFileVersionInfoW(str(path), 0, size, buffer):
        raise IdentityError(f"could not read PE VERSIONINFO: {path}")

    def query(block: str) -> tuple[ctypes.c_void_p, int]:
        pointer = ctypes.c_void_p()
        length = ctypes.c_uint()
        if not version.VerQueryValueW(buffer, block, ctypes.byref(pointer), ctypes.byref(length)):
            raise IdentityError(f"PE VERSIONINFO is missing {block}")
        return pointer, length.value

    fixed_pointer, _ = query("\\")
    fixed = ctypes.cast(fixed_pointer, ctypes.POINTER(_VsFixedFileInfo)).contents

    def dotted(ms: int, ls: int) -> str:
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"

    translation_pointer, translation_length = query("\\VarFileInfo\\Translation")
    if translation_length < 4:
        raise IdentityError("PE VERSIONINFO translation table is malformed")
    translation = ctypes.cast(translation_pointer, ctypes.POINTER(ctypes.c_uint16))
    language_and_codepage = f"{translation[0]:04x}{translation[1]:04x}"

    values = {
        "FileVersionFixed": dotted(fixed.file_version_ms, fixed.file_version_ls),
        "ProductVersionFixed": dotted(fixed.product_version_ms, fixed.product_version_ls),
    }
    for field in (
        "CompanyName", "FileDescription", "FileVersion", "InternalName",
        "OriginalFilename", "ProductName", "ProductVersion",
    ):
        pointer, length = query(f"\\StringFileInfo\\{language_and_codepage}\\{field}")
        values[field] = ctypes.wstring_at(pointer, length).rstrip("\0")
    # Optional field: absent on a stable signed build, required on a prerelease.
    try:
        pointer, length = query(
            f"\\StringFileInfo\\{language_and_codepage}\\SpecialBuild"
        )
        values["SpecialBuild"] = ctypes.wstring_at(pointer, length).rstrip("\0")
    except IdentityError:
        values["SpecialBuild"] = ""
    values["FileFlags"] = fixed.file_flags & fixed.file_flags_mask
    return values


def _verify_pe(path: Path, identity: Mapping[str, str]) -> dict[str, str]:
    values = _read_pe_identity(path)
    executable_stem = Path(identity["desktop_executable"]).stem
    expected = {
        "CompanyName": identity["publisher"],
        "FileDescription": identity["file_description"],
        "FileVersion": identity["windows_version"],
        "FileVersionFixed": identity["windows_version"],
        "InternalName": executable_stem,
        "OriginalFilename": identity["desktop_executable"],
        "ProductName": identity["product_name"],
        "ProductVersion": identity["windows_version"],
        "ProductVersionFixed": identity["windows_version"],
    }
    if identity["special_build"]:
        expected["SpecialBuild"] = identity["special_build"]
    _expect("PE filename", path.name, identity["desktop_executable"])
    for field, expected_value in expected.items():
        _expect(f"PE {field}", values[field], expected_value)
    if identity["prerelease"] == "yes":
        vs_ff_prerelease, vs_ff_specialbuild = 0x2, 0x20
        flags = int(values["FileFlags"])
        missing = [
            name for name, bit in (
                ("VS_FF_PRERELEASE", vs_ff_prerelease),
                ("VS_FF_SPECIALBUILD", vs_ff_specialbuild),
            ) if not flags & bit
        ]
        if missing:
            raise IdentityError(
                f"PE FILEFLAGS 0x{flags:x} is missing {', '.join(missing)}; "
                f"manifest channel is {identity['channel']}"
            )
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "packaging" / "release-manifest.json")
    parser.add_argument("--pe", type=Path)
    args = parser.parse_args(argv)

    try:
        identity = _manifest_identity(_read_manifest(args.manifest.resolve()))
        _verify_sources(identity)
        receipt: dict[str, object] = {"result": "PASS", "identity": identity}
        if args.pe is not None:
            receipt["pe"] = _verify_pe(args.pe.resolve(), identity)
    except IdentityError as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
