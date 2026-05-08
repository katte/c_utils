# String EOL Setter for C/C++

Uno strumento robusto in Python per normalizzare i terminatori di riga (`\n` <-> `\r\n`) esclusivamente all'interno delle stringhe letterali contenute in chiamate a funzione o macro C/C++.

## 💡 Perché questo tool?

A differenza di un semplice "cerca e sostituisci" globale, questo script:
- **Analizza il codice (Lexing):** Ignora stringhe all'interno di commenti (singola riga `//` o blocco `/* ... */`) e costanti di carattere (es. `'\n'`).
- **Targeting Mirato:** Agisce solo sulle stringhe passate come argomenti a funzioni (es. `printf`, `fprintf`, `LOG`, ecc.).
- **Correzione Errori:** Gestisce e corregge automaticamente il typo comune `\n\r` normalizzandolo in `\r\n` (o `\n`).
- **Performance:** Ottimizzato per codebase di grandi dimensioni grazie all'uso della ricerca binaria (`bisect`) per il calcolo delle righe.

## 🚀 Caratteristiche

- ✅ Conversione bidirezionale: `--to-crlf` o `--to-lf`.
- ✅ Modalità `--dry-run` per vedere le modifiche senza applicarle.
- ✅ Filtro per estensioni file (es. `.c`, `.h`, `.cpp`).
- ✅ Filtro per nomi funzione specifici (es. `--only PRINTF`).
- ✅ Esclusione intelligente delle cartelle (es. `build`, `.git`).
- ✅ Supporto per encoding UTF-8 e Latin-1.

## 🛠 Installazione

Non sono richieste dipendenze esterne. È sufficiente avere Python 3.6+ installato.

```bash
git clone [https://github.com/katte82/c_string-eol-setter.git](https://github.com/katte82/c_string-eol-setter.git)
cd string-eol-setter
```

## 📖 Utilizzo

### Esempi Comuni

**Convertire tutte le stringhe in `\r\n` per i file .c e .h nella cartella corrente:**
```bash
python main.py --to-crlf . --ext c --ext h
```

**Convertire in `\n` solo all'interno delle macro `PRINTF`, mostrando solo un'anteprima:**
```bash
python main.py --to-lf --only PRINTF --dry-run
```

**Eseguire su una cartella specifica escludendo i file di output:**
```bash
python main.py --to-crlf ./src --exclude out --exclude temp
```

### Argomenti CLI

| Argomento | Descrizione |
| :--- | :--- |
| `root` | Cartella radice da scansionare (default: `.`) |
| `--to-crlf` | Converte `\n` in `\r\n`. |
| `--to-lf` | Converte `\r\n` in `\n`. |
| `--dry-run` | Mostra le modifiche pianificate senza scrivere sui file. |
| `--ext <ext>` | Include solo file con l'estensione indicata (es. `c`). Ripetibile. |
| `--exclude <dir>` | Cartelle da ignorare durante la scansione. |
| `--only <name>` | Applica le modifiche solo alle chiamate della funzione/macro specificata. |

## 🛡 Casi Gestiti

Il tool è progettato per gestire in modo sicuro:
- **Commenti:** `printf("ciao\n"); // questo \n non viene toccato`
- **Typo storici:** `\n\r` viene rilevato e trasformato correttamente in base alla modalità scelta (es. `\n\r` -> `\r\n`).
- **Escape multipli:** Gestisce correttamente sequenze come `\\n` (backslash letterale seguito da n), evitando sostituzioni errate.

## 📄 Licenza

Questo progetto è rilasciato sotto licenza MIT.
```