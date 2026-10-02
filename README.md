# RPCS3 PS5 / ZER0DAY

Port sperimentale di RPCS3 per PS5/Prospero con frontend homebrew nativo, catalogo USB e integrazione OpenProspero.

## Contenuto della repository

- `src/`, `include/`, `core/`, `cmake/`: codice del frontend/homebrew e bridge RPCS3.
- `scripts/`: preparazione dipendenze, patch, build del core, build PS5 e packaging.
- `tests/`: test host e controlli strutturali.
- `docs/`: stato dell'integrazione, provenienza dipendenze e note tecniche.
- `assets/`, `third_party/`: asset e sorgenti locali necessari al frontend.
- `deps/`: dipendenze upstream recuperate in modo riproducibile dagli script/manifest; non vengono committati build intermedi o cache.

## Build

Prerequisiti host: Linux/WSL x86_64, Clang/LLD 19, CMake 3.28+, Ninja, Python 3, Make, binutils, OpenSSL, zlib e libpng.

```sh
bash scripts/prepare.sh
bash scripts/build_ps5.sh
python3 -m unittest discover -s tests -v
bash scripts/package_ps5.sh --structural-only
```

La base RPCS3 è fissata alla revisione `17320679e329908af40b76a8a48c43025d4acc9a`. Le patch locali sono versionate in `core/patches/`.

## Stato

Il core C++ RPCS3 è collegato all'applicazione PS5. Il frontend USB e il bridge sono compilati; l'esecuzione runtime su console resta sperimentale. Le prove e i limiti sono documentati in `docs/BUILD-STATUS.md`.

## Licenze

Il nuovo codice di questo port è GPL-3.0-or-later. RPCS3 e le altre dipendenze mantengono le rispettive licenze upstream.
