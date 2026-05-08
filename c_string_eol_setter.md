# String EOL Setter for C/C++

A robust Python tool to normalize line-ending terminators (`\n` <-> `\r\n`) exclusively within string literals contained in C/C++ function calls or macros.

## 💡 Why This Tool?

Unlike a simple "find and replace" globally, this script:
- **Analyzes Code (Lexing):** Ignores strings within comments (single-line `//` or block `/* ... */`) and character constants (e.g., `'\n'`).
- **Targeted Targeting:** Acts only on strings passed as arguments to functions (e.g., `printf`, `fprintf`, `LOG`, etc.).
- **Error Correction:** Automatically handles and corrects the common typo `\n\r`, normalizing it to `\r\n` (or `\n`).
- **Performance:** Optimized for large codebases thanks to binary search (`bisect`) for line number calculations.

## 🚀 Features

- ✅ Bidirectional conversion: `--to-crlf` or `--to-lf`.
- ✅ `--dry-run` mode to see changes without applying them.
- ✅ Filter by file extensions (e.g., `.c`, `.h`, `.cpp`).
- ✅ Filter by specific function names (e.g., `--only PRINTF`).
- ✅ Smart folder exclusion (e.g., `build`, `.git`).
- ✅ Support for UTF-8 and Latin-1 encodings.

## 🛠 Installation

No external dependencies required. Just have Python 3.6+ installed.

```bash
git clone https://github.com/katte82/c_string-eol-setter.git
cd string-eol-setter
```

## 📖 Usage

### Common Examples

**Convert all strings to `\r\n` for .c and .h files in the current directory:**
```bash
python c_string_eol_setter.py --to-crlf . --ext c --ext h
```

**Convert to `\n` only inside the `PRINTF` macro, showing only a preview:**
```bash
python c_string_eol_setter.py --to-lf --only PRINTF --dry-run
```

**Run on a specific folder excluding output files:**
```bash
python c_string_eol_setter.py --to-crlf ./src --exclude out --exclude temp
```

### CLI Arguments

| Argument | Description |
| :--- | :--- |
| `root` | Root folder to scan (default: `.`) |
| `--to-crlf` | Converts `\n` to `\r\n`. |
| `--to-lf` | Converts `\r\n` to `\n`. |
| `--dry-run` | Shows planned changes without writing to files. |
| `--ext <ext>` | Include only files with the specified extension (e.g., `c`). Repeatable. |
| `--exclude <dir>` | Folders to ignore during scanning. |
| `--only <name>` | Apply changes only to the specified function/macro calls. |

## 🛡 Handled Cases

The tool is designed to safely handle:
- **Comments:** `printf("hello\n"); // this \n is not touched`
- **Historical Typos:** `\n\r` is detected and transformed correctly based on the chosen mode (e.g., `\n\r` -> `\r\n`).
- **Multiple Escapes:** Correctly handles sequences like `\\n` (literal backslash followed by n), avoiding incorrect substitutions.

## 📄 License

This project is released under the MIT License.
```