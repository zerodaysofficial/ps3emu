#!/usr/bin/env python3
"""Stage a reproducible, self-contained development checkpoint ZIP."""
import argparse
import hashlib
import json
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (2026, 10, 2, 0, 0, 0)


def copy_tree(source, target, omit=(), omit_root=()):
    omit = set(omit) | {".git", "__pycache__", ".DS_Store"}
    for path in sorted(source.rglob("*")):
        rel = path.relative_to(source)
        if any(part in omit for part in rel.parts) or rel.parts[0] in omit_root:
            continue
        dest = target / rel
        if path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def stage(vendor, target):
    if target.exists():
        raise ValueError(f"Staging directory already exists: {target}")
    target.mkdir(parents=True)
    tracked = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"])
    for name in tracked.decode().split("\0"):
        if name:
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, dest)
    deps = target / "deps"
    sdk = vendor / ("openprospero" if (vendor / "openprospero").is_dir() else "sdk")
    copy_tree(sdk, deps / "openprospero", omit_root={"build"})
    for name in ("crt1.o", "nativeaot_compat.o", "openprospero_companion_autostart.o"):
        (deps / "openprospero/sdk/target/lib" / name).unlink(missing_ok=True)
    for dep in ("sdl", "quickjs", "nlohmann_json", "pugixml", "lzma_sdk"):
        source = sdk / f"offline/{dep}-src"
        if not source.is_dir():
            source = sdk / f"build/_deps/{dep}-src"
        copy_tree(source, deps / f"openprospero/offline/{dep}-src")
    for name in ("prospero", "prospero-link", "prospero-stub"):
        dest = deps / "openprospero/build/bin" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sdk / "build/bin" / name, dest)
    dest = deps / "openprospero/build/lib/libopenprospero.so"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sdk / "build/lib/libopenprospero.so", dest)
    graphics_source = vendor / ("ps5-opengl" if (vendor / "ps5-opengl").is_dir() else "ps5-opengl-1.0.0")
    copy_tree(graphics_source, deps / "ps5-opengl", omit_root={"build"})
    graphics = vendor / ("ps5-opengl-sdk" if (vendor / "ps5-opengl-sdk").is_dir() else "ps5-opengl-sdk-1.0.0")
    copy_tree(graphics / "sdk/include", deps / "ps5-opengl-sdk/sdk/include")
    copy_tree(graphics / "sdk/lib", deps / "ps5-opengl-sdk/sdk/lib")
    copy_tree(graphics / "LICENSES", deps / "ps5-opengl-sdk/LICENSES")
    copy_tree(graphics / "sources", deps / "ps5-opengl-sdk/sources")
    for name in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "dependencies.json"):
        if (graphics / name).is_file():
            shutil.copy2(graphics / name, deps / "ps5-opengl-sdk" / name)
    for name in ("provenance.json", "runtime-config.txt", "consumer-validation.json"):
        if (graphics / name).is_file():
            shutil.copy2(graphics / name, deps / "ps5-opengl-sdk" / name)
    copy_tree(vendor / "rpcs3-official", deps / "rpcs3-official", omit_root={"build"})
    copy_tree(vendor / "core-extra", deps / "core-extra", omit_root={"build"})
    copy_tree(vendor / "SharpProspero", deps / "SharpProspero", omit={"bin", "obj"})
    revisions = {"rpcs3-official": "17320679e329908af40b76a8a48c43025d4acc9a",
                 "SharpProspero": "5dfdb4b0b166e83dc9ae275001afb695f12c7174",
                 "openprospero/third_party/openagc": "30a503b9838c767c0c8533e7886b06509c959ea3"}
    (deps / "SNAPSHOTS.json").write_text(json.dumps(revisions, indent=2) + "\n")
    release = target / "release"
    release.mkdir()
    shutil.copy2(ROOT / "build/ps5/eboot.bin", release / "eboot.bin")
    packages = sorted((ROOT / "build/ps5").glob("package-*/*.pkg"))
    if not packages:
        raise ValueError("No OPSDK package was produced")
    shutil.copy2(packages[-1], release / "core-linked-STRUCTURAL-ONLY.pkg")
    for size in ("720", "1080"):
        image = ROOT / f"build/preview-{size}.png"
        if not image.is_file():
            image = ROOT / f"release/preview-{size}.png"
        if image.is_file():
            shutil.copy2(image, release / f"desktop-preview-{size}.png")
    proof = ROOT / "build/core-ps5/core-link-proof.json"
    if not proof.is_file():
        raise ValueError("Verified final core link proof is missing")
    record = json.loads(proof.read_text())
    if record["application_sha256"] != digest(release / "eboot.bin"):
        raise ValueError("Core link proof does not match the packaged application")
    for name in ("core-link-proof.json", "application.map", "compile_commands.json"):
        shutil.copy2(ROOT / "build/core-ps5" / name, release / name)
    shutil.copy2(ROOT / "build/core-ps5/emu/librpcs3_emu.a", release / "librpcs3_emu.a")
    (release / "STRUCTURAL-ONLY.txt").write_text(
        "Original complete RPCS3 C++ target linked into the application.\n"
        "Game video, audio and input use original Null providers.\n"
        "Runtime modules absent. Package install/launch and firmware compatibility unverified.\n"
        "Generated only by OPSDK's experimental writer, with --no-companion.\n")
    subprocess.run(["git", "-C", str(ROOT), "bundle", "create",
                    str(release / "project-history.bundle"), "--all"], check=True)
    (release / "SHA256SUMS").write_text("".join(
        f"{digest(f)}  {f.name}\n" for f in sorted(release.iterdir()) if f.is_file()))
    copy_tree(ROOT / "logs", target / "logs")
    notice = ("This ZIP contains the original RPCS3 C++ core linked to the native frontend.\n"
              "Game video/audio/input use Null providers; console execution is unverified.\n"
              "No runtime firmware modules or commercial games are included.\n"
              "See README.md, docs/BUILD-STATUS.md and original dependency licenses.\n")
    (target / "CHECKPOINT.txt").write_text(notice)
    files = [f for f in sorted(target.rglob("*")) if f.is_file()]
    manifest = {"format": 1, "project_commit": subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "status": "original core linked; Null game providers; package structural only; console unverified",
        "files": [{"path": str(f.relative_to(target)), "bytes": f.stat().st_size,
                   "sha256": digest(f)} for f in files]}
    (target / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")


def archive(target, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6,
                         allowZip64=True) as z:
        for f in sorted(target.rglob("*")):
            if not f.is_file():
                continue
            name = str(Path(target.name) / f.relative_to(target))
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | stat.S_IMODE(f.stat().st_mode)) << 16
            with f.open("rb") as src, z.open(info, "w", force_zip64=True) as dest:
                shutil.copyfileobj(src, dest, 1024 * 1024)
    with zipfile.ZipFile(out) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP CRC validation failed")
        if any(Path(n).is_absolute() or ".." in Path(n).parts for n in z.namelist()):
            raise ValueError("Unsafe archive path")
    print(f"ZIP verified: {out} ({out.stat().st_size} bytes)")
    print("SHA256 " + digest(out))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vendor", type=Path, required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    stage(args.vendor.resolve(), args.stage.resolve())
    archive(args.stage.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
