# RPCS3 PS5 / ZER0DAY

Port sperimentale di RPCS3 per PS5/Prospero con frontend homebrew nativo, catalogo USB e integrazione OpenProspero.

## Cosa contiene questa repository

Il codice specifico del port è versionato direttamente:

- `src/` — frontend/homebrew PS5, scanner USB, UI EGL/OpenGL e runtime shims.
- `include/` — API C del frontend e bridge.
- `core/` — bridge C++ verso RPCS3, callback, CMake del core e patch PS5.
- `cmake/` — toolchain `x86_64-sie-ps5` e finder target.
- `scripts/` — bootstrap sorgenti, build OpenProspero, FFmpeg/core, verifica e packaging.
- `tests/` — regressioni del catalogo, UI, callback, linker e ABI.
- `docs/` — provenienza, revisioni e stato tecnico.

RPCS3, OpenProspero, ps5-opengl, SharpProspero e le altre dipendenze upstream sono molto più grandi del port stesso. Non vengono duplicati come build/cache dentro Git: `scripts/bootstrap_sources.sh` recupera i sorgenti alle revisioni registrate e verifica gli hash degli archivi esterni.

## Bootstrap completo

Prerequisiti principali: Linux/WSL x86_64, Git, curl, tar, Python 3 + Pillow, Clang/LLD 19, CMake 3.28+, Ninja, Make, binutils, OpenSSL, zlib e libpng development headers.

```sh
git clone https://github.com/zerodaysofficial/ps3emu.git
cd ps3emu
bash scripts/bootstrap_sources.sh
bash scripts/prepare.sh
bash scripts/build_ps5.sh
python3 -m unittest discover -s tests -v
bash scripts/package_ps5.sh --structural-only
```

Per un package con runtime applicativo, `scripts/package_ps5.sh` cerca i moduli autorizzati dell'utente in `private-runtime/`. Nessun modulo firmware proprietario, chiave o contenuto commerciale è incluso nella repository.

## Revisioni principali

- RPCS3: `17320679e329908af40b76a8a48c43025d4acc9a`
- SharpProspero: `5dfdb4b0b166e83dc9ae275001afb695f12c7174`
- ps5-opengl v1.0.0: `dce74910af7f4274c48d05e0ae001b3038462588`
- OpenAGC: `30a503b9838c767c0c8533e7886b06509c959ea3`

Vedi `docs/DEPENDENCIES.md` e `docs/SOURCE-BOOTSTRAP.md` per la provenienza completa.

## Stato del port

Il target C++ RPCS3 originale viene compilato per `x86_64-sie-ps5` e collegato al frontend tramite `Emulator::Init`, `BootGame` e `Kill`. Gli interpreti PPU/SPU restano quelli upstream. In questa fase renderer/audio/input del gioco sono impostati sui provider Null originali mentre il menu usa EGL/ps5-opengl.

L'esecuzione su console è ancora sperimentale: i log hardware hanno già permesso di correggere diversi problemi del loader/runtime, ma la compatibilità completa dei giochi non è dichiarata. Vedi `docs/BUILD-STATUS.md`.

## Licenze

I file del port mantengono i rispettivi identificatori SPDX. RPCS3 e ogni dipendenza upstream mantengono le proprie licenze; le notices e la provenienza sono documentate accanto ai componenti interessati.
