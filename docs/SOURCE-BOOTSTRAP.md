# Source bootstrap

The repository keeps the PS5/RPCS3 port, patches, build scripts and tests in Git. Large upstream projects are fetched at pinned revisions instead of committing generated build trees and duplicate vendor archives.

Run:

```sh
bash scripts/bootstrap_sources.sh
```

The bootstrap populates:

- RPCS3 at `17320679e329908af40b76a8a48c43025d4acc9a` plus its required submodules.
- SharpProspero at `5dfdb4b0b166e83dc9ae275001afb695f12c7174`.
- ps5-opengl v1.0.0 source at commit `dce74910af7f4274c48d05e0ae001b3038462588`.
- the official ps5-opengl SDK 1.0.0 release after SHA-256 verification.
- Abseil 20250512.1, FFmpeg 8.1.1, GLEW 2.2.0 and GNU libiconv 1.18 after SHA-256 verification.
- OpenProspero from `https://github.com/OpenProspero/sdk.git` by default. Set `OPENPROSPERO_REPO` and `OPENPROSPERO_REF` when reproducing the exact historical SDK snapshot.

After bootstrap:

```sh
bash scripts/prepare.sh
bash scripts/build_ps5.sh
python3 -m unittest discover -s tests -v
bash scripts/package_ps5.sh --structural-only
```

`private-runtime/` is intentionally ignored. No Sony firmware runtime modules, commercial games, keys, or decrypted proprietary components belong in this repository.
