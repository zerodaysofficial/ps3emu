# Dipendenze e provenienza

| Componente | Origine / revisione | Impiego |
|---|---|---|
| RPCS3 ufficiale | `https://github.com/RPCS3/rpcs3`, `17320679e329908af40b76a8a48c43025d4acc9a` | Target C++23 completo compilato e collegato per PS5 |
| OPSDK | Archivio `openprosperosdk.rar` caricato dall'utente, SHA-256 `4f19154a9f04d71d242acd460a99843c46048370ce2e22af4ab7148d8416afe3` | CRT, stub, link applicazione e writer del pacchetto |
| OpenAGC | `https://github.com/OpenProspero/AGC`, `30a503b9838c767c0c8533e7886b06509c959ea3` | Dipendenza host OPSDK richiesta dal suo CMake |
| ps5-opengl sorgente | Archivio utente `ps5-opengl-1.0.0.zip`, SHA-256 `562e3c44ddd723346fcacc5a054a64ada04bb67f0eddd7183776e3a4f1ba1ea2` | Sorgenti driver, allocator nativo e notices |
| ps5-opengl SDK | Release ufficiale `v1.0.0`, SHA-256 archivio `f93643c04c843d56143b00951df1f8042ea7706ae9f19e4e9abf158e1ead77c5` | Header EGL/GL, librerie target e due stub AGC generati |
| SharpProspero | `https://github.com/SvenGDK/SharpProspero`, `5dfdb4b0b166e83dc9ae275001afb695f12c7174` | Riferimento verificato per API applicazione, pad e VideoOut |
| stb_image | Submodule RPCS3 `013ac3beddff3dbffafd5177e7972067cd2b5083` | Decodifica PNG limitata per le copertine |
| DejaVu Sans | Font di sistema, licenza in `assets/FONT-LICENSE.txt` | Atlante ASCII/Latin-1 del renderer |

URL dell'SDK grafico:
`https://github.com/blackbearreloaded/ps5-opengl/releases/download/v1.0.0/ps5-opengl-sdk-1.0.0.tar.gz`.
Il suo `dependencies.json`, i patch e `THIRD_PARTY_NOTICES.md` indicano gli
upstream grafici e i sorgenti corrispondenti. Il ZIP include header/librerie usati
dal frontend, i sorgenti originali del driver e le notices; non tutti gli esempi
e gli SDK opzionali della release grafica.
Gli archivi dei sorgenti corrispondenti forniti dalla release, inclusi Mesa e
OpenGNM PSBC, sono conservati in `deps/ps5-opengl-sdk/sources/`, con la provenienza
e i relativi hash originali.

Lo snapshot RPCS3 include tutti i submodule selezionati dal grafo di questa
build. `rpcs3-submodules.txt` conserva il rilevamento del vecchio checkpoint;
`core-dependencies.json` registra revisioni, URL e SHA-256 degli archivi
aggiunti per il core completo. Il vecchio ZIP
RPCS3 0.0.43 non è la base compilata di questo checkpoint; la base è il repository
ufficiale fissato sopra. Nessun branch upstream `freebsd` è stato inventato.

## Correzioni locali OPSDK

`scripts/prepare_sdk.py` applica in modo idempotente:

1. Conversione CRLF→LF negli script shell e nei manifest degli stub caricati.
2. Aggiunta di `<optional>` in `src/packaging/pfs.cpp`, richiesta dalla build.
3. Due import VideoOut aggiuntivi richiesti dal driver: `sceVideoOutGetResolutionStatus`
   e `sceVideoOutGetOutputStatus`. Sono dichiarazioni, non implementazioni.
4. Applicazione del patch `core/patches/openprospero-weak-imports.patch`: i simboli
   ELF weak privi di provider vengono associati a zero da LLD prima della
   conversione SCE. I simboli obbligatori irrisolti restano errori di link e i
   provider weak disponibili restano import. Tre fixture del linker reale
   verificano questi casi.

I due stub AGC dell'SDK grafico vengono copiati nel sysroot OPSDK per consentire
al resolver di leggere i provider. Non si collegano stub statici SharpProspero
né il suo toolchain NativeAOT. Le funzioni opzionali Mesa di cache temporanea e
sottoprocessi non disponibili restituiscono `ENOSYS`; il frontend non le abilita.
L'heap del driver viene usato senza modifiche con tutti e sei i wrap previsti.

## Sorgenti host OPSDK offline

| Componente | Revisione |
|---|---|
| SDL3 | `7f3ae3d57459e59943a4ecfefc8f6277ec6bf540` |
| QuickJS-ng | `58bdcf0ce35594df30bf5cfbba3be8b454799cc0` |
| pugixml | `ee86beb30e4973f5feffe3ce63bfa4fbadf72f38` |
| LZMA-SDK | `781863cdf592da3e97420f50de5dac056ad352a5` |
| nlohmann/json | `9cca280a4d0ccf0c08f47a99aa71d1b0e52f8d03` |

I sorgenti scaricati dal CMake OPSDK sono inclusi in `deps/openprospero/offline/`
e selezionati da `prepare.sh` tramite `FETCHCONTENT_SOURCE_DIR_*`.
Non serve un `protoc` host: le unità protobuf generate sono già nello snapshot.
LLVM, Qt, Vulkan e SDL per RPCS3 sono disabilitati in questa build. Le licenze
originali restano accanto ai sorgenti.

## Dipendenze del core

Oltre ad AsmJit, yaml-cpp, pugixml, stb, Fusion e zlib già presenti, sono inclusi
e compilati i submodule fissati di FFmpeg-core, glslang, libpng, protobuf, zstd,
SoundTouch, miniupnp, cubeb, libusb, curl, RtMidi, wolfSSL e OpenAL. Le revisioni
esatte sono quelle del repository RPCS3 fissato, elencate in
`core-dependencies.json` con gli hash degli archivi recuperati.

| Sorgente aggiuntivo | Versione | Impiego |
|---|---|---|
| Abseil | 20250512.1 | Versione richiesta dal protobuf fissato |
| FFmpeg | 8.1.1 | Librerie statiche target compatibili con FFmpeg-core, codec selezionati |
| GLEW | 2.2.0 | Sorgente originale, compilato con EGL e senza GLU |
| GNU libiconv | 1.18 | Conversioni reali di cellL10n, libcharset e header target generati |

Le librerie desktop non sono riutilizzate nel target. OpenAL usa il backend
originale senza dispositivo; libusb usa il backend upstream null_usb con
passthrough indisponibile. Le normali USB montate del catalogo usano il
filesystem dell'applicazione. Il link comprende le librerie libc/C++ del SDK
e gli stub dei provider effettivamente dichiarati, incluso ScePosixForWebKit.
La disponibilità sul firmware di destinazione richiede ancora verifica.

## Patch RPCS3 e identificazione della build

`core/patches/rpcs3-ps5.patch` modifica quattro sorgenti originali, soltanto
nel ramo `__PROSPERO__`: percorsi di configurazione/cache applicazione,
normalizzazione delle impostazioni agli interpreti e provider Null,
separazione del pad originale dagli handler Qt/HID e degli eventi mouse Qt.
Le implementazioni originali del core restano nel target completo.
`core/compat/sys/stdint.h` corregge l'ordine di include del SDK senza ridefinire
tipi interi. Gli script verificano che i patch siano applicabili o già applicati.

Il file git-version.h generato usa `0-17320679`, ramo `ps5-core` e local_build.
Lo zero indica che il conteggio locale dei commit upstream non è disponibile;
la revisione completa è registrata nella prova del link. Non è un numero di
build ufficiale RPCS3. Il link di rilascio elimina DWARF, mantenendo i simboli
per la verifica e la mappa con le provenienze degli oggetti.
