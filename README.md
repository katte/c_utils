# C/C++ Utilities

A collection of robust Python tools for normalizing and formatting C/C++ code. These tools use lexical analysis (lexing) to ensure safe transformations that never affect comments, character literals, or string contents.

## Tools Overview

### 1. String EOL Setter (`c_string_eol_setter.py`)

A robust Python tool for normalizing line-ending sequences (`\n` <-> `\r\n`) exclusively within string literals in C/C++ function calls or macros.

#### Why This Tool?

Unlike a simple "find and replace" globally:
- **Code Analysis (Lexing):** Ignores strings inside comments (single-line `//` or block `/* ... */`) and character constants (e.g., `'\n'`).
- **Targeted Transformation:** Operates only on strings passed as arguments to functions (e.g., `printf`, `fprintf`, `LOG`, etc.).
- **Error Correction:** Automatically detects and corrects the common typo `\n\r`, normalizing it to `\r\n` (or `\n`).
- **Performance:** Optimized for large codebases using binary search (`bisect`) for line number calculations.

#### Features

- ✅ Bidirectional conversion: `--to-crlf` or `--to-lf`.
- ✅ `--dry-run` mode to preview changes without applying them.
- ✅ File extension filtering (e.g., `.c`, `.h`, `.cpp`).
- ✅ Filter by specific function names (e.g., `--only PRINTF`).
- ✅ Smart directory exclusion (e.g., `build`, `.git`).
- ✅ Support for UTF-8 and Latin-1 encodings.

#### Installation

No external dependencies required. Python 3.6+ is sufficient.

```bash
git clone https://github.com/katte82/c_string-eol-setter.git
cd string-eol-setter
```

#### Usage

**Common Examples:**

Convert all strings to `\r\n` for .c and .h files in the current directory:
```bash
python c_string_eol_setter.py --to-crlf . --ext c --ext h
```

Convert to `\n` only inside `PRINTF` macros, showing a preview:
```bash
python c_string_eol_setter.py --to-lf --only PRINTF --dry-run
```

Run on a specific folder, excluding output files:
```bash
python c_string_eol_setter.py --to-crlf ./src --exclude out --exclude temp
```

#### CLI Arguments

| Argument | Description |
| :--- | :--- |
| `root` | Root folder to scan (default: `.`) |
| `--to-crlf` | Converts `\n` to `\r\n`. |
| `--to-lf` | Converts `\r\n` to `\n`. |
| `--dry-run` | Shows planned changes without writing to files. |
| `--ext <ext>` | Include only files with the specified extension (e.g., `c`). Repeatable. |
| `--exclude <dir>` | Folders to ignore during scanning. |
| `--only <name>` | Apply changes only to the specified function/macro calls. |

#### Handled Cases

The tool safely handles:
- **Comments:** `printf("hello\n"); // this \n is not touched`
- **Historical Typos:** `\n\r` is detected and transformed correctly (e.g., `\n\r` -> `\r\n`).
- **Multiple Escapes:** Correctly handles sequences like `\\n` (literal backslash followed by n), avoiding incorrect substitutions.

#### License

This project is released under the MIT License.

---

### 2. C/C++ Brace Formatter (`c_brace_formatter.py`)

An intelligent Python tool for normalizing brace positioning in control statements (`if`, `else`, `for`, `while`, `switch`).

Unlike simple text substitutions, this script uses a **Lexer (lexical analyzer)** to identify code components, ensuring that changes never affect the contents of strings, comments, or macros.

#### Features

- **Multi-Style Support:** Switch from "K&R" style (brace on the same line) to "Allman" style (brace on a new line) and vice versa.
- **Safe Analysis:** Recognizes comments (`//` and `/* */`) between the keyword and brace, preserving or moving them correctly.
- **Automatic Indentation:** In `--new-line` mode, calculates correct indentation to place the brace exactly under the reference keyword.
- **Extended Targeting:** Handles not only `if/else` but also loops (`for`, `while`) and `switch` blocks.

#### Usage Modes

##### 1. "Same Line" Style (K&R / Java)

Transforms code by moving the brace to the same line as the condition.

**Command:**
```bash
python c_brace_formatter.py . --ext c --same-line
```

**Example transformation:**
```c
// BEFORE
if (condition)
{
    ...
}
// AFTER
if (condition) {
    ...
}
```

##### 2. "New Line" Style (Allman / BSD)

Transforms code by moving the brace to a new line, aligned vertically with the statement.

**Command:**
```bash
python c_brace_formatter.py . --ext c --new-line
```

**Example transformation:**
```c
// BEFORE
if (condition) {
    ...
}
// AFTER
if (condition)
{
    ...
}
```

#### CLI Arguments

| Argument | Description |
| :--- | :--- |
| `root` | Root folder to scan (default: `.`). |
| `--same-line` | **Required** (or `--new-line`): Move braces to the condition line. |
| `--new-line` | **Required** (or `--same-line`): Move braces to the next line. |
| `--dry-run` | Show changes to console without writing to files. |
| `--ext <ext>` | Filter by extension (e.g., `--ext c --ext h`). |
| `--exclude <dir>` | Ignore specific folders (default: `.git`, `build`, `out`). |

#### Safety and Edge Cases

The script is designed to skip formatting a single block if it detects ambiguous situations, such as:
- **Inline Comments (`//`):** If a comment prevents moving a brace to the same line without "commenting it out", the script skips the change.
- **Complex Macros:** If non-recognized tokens (e.g., multi-line macros with `\`) appear between the parenthesis and brace, the block is skipped for safety.
- **Strings:** Braces inside strings (e.g., `printf("{");`) are never touched.

#### License

Released under the MIT License.

---

## Project Structure

```
c_utils/
├── README.md                      # This file
├── c_string_eol_setter.md        # Detailed documentation (English)
├── c_string_eol_setter.py        # String EOL normalization tool
├── c_brace_formatter.md          # Detailed documentation (English)
├── c_brace_formatter.py          # Brace formatter tool
└── LICENSE                        # MIT License
```

## License

All tools in this repository are released under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please ensure your changes maintain the safety and robustness of the lexical analysis.
