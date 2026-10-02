# Stato verificato dell'integrazione

Data: 2 ottobre 2026. Il core C++ originale è collegato all'applicazione PS5.
Il risultato riguarda compilazione, link e struttura degli artefatti; nessuna
console è stata contattata e nessun gioco è stato eseguito.

| Componente | Risultato osservato | Limite della prova |
|---|---|---|
| Catalogo USB | 14 test su file temporanei reali | Mount USB PS5 non eseguiti |
| Modello UI/controller | 10 test | Input del menu, senza input PS3 |
| Shim Mesa | 3 test | Cache disco/subprocessi opzionali indisponibili |
| Renderer/anteprima | 4 test di integrazione | Frontend host; EGL PS5 non eseguito |
| Budget decoder | 2 test, limite 32 MiB | Copertine oltre budget usano il fallback |
| Header target | Include stdint/inttypes in entrambi gli ordini compilato con Clang PS5 | ABI verificata in compilazione |
| Coda callback | Thread reale, limite, chiusura, thread errato e conservazione dopo eccezione e drain annidato | Esecuzione host dello stesso componente |
| Dialoghi di messaggistica | Factory callback originali, risultati di annullamento e payload invariato verificati | Esecuzione host con le vere interfacce RPCS3 |
| Richiesta di avvio | Percorsi USB, dimensioni e ID validati con codice C++ reale | Nessuna esecuzione di EBOOT.BIN |
| Linker OPSDK | Tre fixture PS5: weak assente, weak disponibile, import obbligatorio mancante | Struttura ELF, senza esecuzione hardware |
| Core RPCS3 | Target originale rpcs3_emu: 477 unità, dipendenze target compilate | Qt/LLVM/Vulkan disabilitati |
| Bridge | Vere funzioni Init, BootGame, Kill trattenute nell'ELF e origine verificata nella mappa | Lifecycle compilato, non eseguito su console |
| ELF finale | Profilo application, tipo 0xfe10, x86_64, 14 header, 5 LOAD allineati a 16 KiB, nessun LOAD W+X | Compatibilità runtime non qualificata |
| Pacchetto | Writer OPSDK sperimentale e lettura interna | Senza runtime; installazione e Publishing Tools non verificati |

La suite comprende 40 test: i 33 originali e sette prove dell'integrazione.
I risultati finali sono in `logs/core-tests-final.log`.
`release/core-link-proof.json` registra revisione RPCS3, conteggio degli oggetti
e SHA-256 dell'archivio e dell'applicazione. La mappa del link e i comandi di
compilazione accompagnano il binario. La verifica fallisce sul precedente
frontend privo del core (`logs/core-link-red.log`).

## Comportamento collegato

Il frontend inizializza RPCS3 sul thread del menu, gestisce le callback dei
worker con una coda limitata e controlla il gioco selezionato prima di chiamare
`BootGame`. L'uscita richiede `Kill` e attende l'arresto reale, pompando le
callback. Il catalogo, il layout e la gestione delle copertine sono conservati.
Le due implementazioni stb_image hanno visibilità separate per mantenere il
budget delle copertine senza duplicare simboli nel link.

I decoder PPU/SPU sono gli interpreti originali. Le configurazioni globali e
per titolo vengono normalizzate al profilo supportato. Renderer, audio,
pad, tastiera, mouse, camera e musica del gioco usano provider Null originali;
alcuni dialoghi e servizi opzionali restituiscono indisponibilità esplicita.
Il menu mantiene EGL/ps5-opengl e il proprio controller nativo.

Il SDK fornisce le API libc supplementari per filesystem e locale C, oltre ai
provider di rete dichiarati nei suoi stub. Nessun risultato di emulazione è
simulato. I simboli ELF weak senza provider vengono associati all'indirizzo
zero dal linker originale LLD; gli import obbligatori mancanti continuano a
produrre errore. La correzione OPSDK è riproducibile e conserva gli import weak
che hanno un provider disponibile.

## Attività ancora necessarie per i giochi

1. Integrare RSX con una superficie EGL e verificare i requisiti GL dei giochi.
2. Implementare l'audio nativo e l'instradamento del controller verso il pad PS3.
3. Qualificare memoria virtuale/JIT, segnali, TLS, thread e filesystem sul runtime.
4. Verificare i moduli importati, incluso il provider POSIX, sul firmware scelto.
5. Provare installazione e avvio del binario identificato dall'hash, poi usare
   contenuti di test autorizzati e firmware PS3 correttamente predisposto.

## Artefatti e questioni precedenti

`release/eboot.bin` contiene il core collegato. Il pacchetto
`release/core-linked-STRUCTURAL-ONLY.pkg` è un contenitore senza runtime.
`release/librpcs3_emu.a` contiene tutte le 477 unità originali configurate.
Gli hash sono in `release/SHA256SUMS` e `MANIFEST.json`. La revisione e le
correzioni delle due regressioni sono documentate in `docs/CORE-REVIEW.md`.

Due dettagli minori già annotati restano aperti: una modifica della sola
`ICON0.PNG` può lasciare in cache una vecchia copertina/fallback; il packaging
riusa `build/ps5/app` e non elimina residui annidati aggiunti manualmente.
Questa integrazione non modifica tali comportamenti. Il pacchetto consegnato
è generato da staging controllato. Le precedenti prove del solo frontend e
gli otto oggetti campione sono superati dalla compilazione e dal link completi.
