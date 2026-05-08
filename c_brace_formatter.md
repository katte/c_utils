# C/C++ Brace Formatter

Uno strumento intelligente in Python per normalizzare la posizione delle parentesi graffe negli statement di controllo (`if`, `else`, `for`, `while`, `switch`). 

A differenza di semplici sostituzioni testuali, questo script utilizza un **Lexer (analizzatore lessicale)** per identificare i componenti del codice, garantendo che le modifiche non tocchino mai il contenuto di stringhe, commenti o macro.

## 🛠 Funzionalità

- **Supporto Multi-Stile**: Passa dallo stile "K&R" (graffa sulla stessa riga) allo stile "Allman" (graffa su riga nuova) e viceversa.
- **Analisi Sicura**: Riconosce i commenti (`//` e `/* */`) tra la keyword e la graffa, preservandoli o spostandoli correttamente.
- **Indentazione Automatica**: Nella modalità `--new-line`, calcola l'indentazione corretta per posizionare la graffa esattamente sotto la keyword di riferimento.
- **Targeting Esteso**: Gestisce non solo `if/else`, ma anche cicli `for`, `while` e blocchi `switch`.

## 📖 Modalità di Utilizzo

### 1. Stile "Same Line" (K&R / Java)
Trasforma il codice portando la graffa sulla stessa riga della condizione.

**Comando:**
```bash
python brace_formatter.py . --ext c --same-line
```

**Esempio di trasformazione:**
```c
// PRIMA
if (condizione)
{
    ...
}
// DOPO
if (condizione) {
    ...
}
```

### 2. Stile "New Line" (Allman / BSD)
Trasforma il codice portando la graffa a capo, allineata verticalmente con lo statement.

**Comando:**
```bash
python brace_formatter.py . --ext c --new-line
```

**Esempio di trasformazione:**
```c
// PRIMA
if (condizione) {
    ...
}
// DOPO
if (condizione)
{
    ...
}
```

## ⚙️ Argomenti CLI

| Argomento | Descrizione |
| :--- | :--- |
| `root` | Cartella radice da scansionare (default: `.`). |
| `--same-line` | **Obbligatorio** (o `--new-line`): Porta le graffe sulla riga della condizione. |
| `--new-line` | **Obbligatorio** (o `--same-line`): Porta le graffe sulla riga successiva. |
| `--dry-run` | Mostra le modifiche a console senza scrivere sui file. |
| `--ext <ext>` | Filtra per estensione (es. `--ext c --ext h`). |
| `--exclude <dir>` | Ignora cartelle specifiche (default: `.git`, `build`, `out`). |

## 🛡 Sicurezza e Casi Limite

Lo script è progettato per interrompere la formattazione di un singolo blocco se rileva situazioni ambigue, come:
- **Commenti in linea (`//`)**: Se un commento impedisce di portare una graffa sulla stessa riga senza "commentarla", lo script salta la modifica.
- **Macro complesse**: Se tra la tonda e la graffa sono presenti token non riconosciuti (es. macro multiriga), il blocco viene ignorato per sicurezza.
- **Stringhe**: Le graffe contenute all'interno di stringhe (es. `printf("{");`) non vengono mai toccate.

## 📄 Licenza

Rilasciato sotto licenza MIT.
```