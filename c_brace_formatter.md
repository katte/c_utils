# C/C++ Brace Formatter

An intelligent Python tool to normalize the positioning of braces in control statements (`if`, `else`, `for`, `while`, `switch`).

Unlike simple text substitutions, this script uses a **Lexer (lexical analyzer)** to identify code components, ensuring that changes never touch the contents of strings, comments, or macros.

## 🛠 Features

- **Multi-Style Support**: Switch from "K&R" style (brace on the same line) to "Allman" style (brace on a new line) and vice versa.
- **Safe Analysis**: Recognizes comments (`//` and `/* */`) between the keyword and brace, preserving or moving them correctly.
- **Automatic Indentation**: In `--new-line` mode, calculates the correct indentation to place the brace exactly under the reference keyword.
- **Extended Targeting**: Handles not only `if/else`, but also loops `for`, `while` and `switch` blocks.

## 📖 Usage Modes

### 1. "Same Line" Style (K&R / Java)
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

### 2. "New Line" Style (Allman / BSD)
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

## ⚙️ CLI Arguments

| Argument | Description |
| :--- | :--- |
| `root` | Root folder to scan (default: `.`). |
| `--same-line` | **Required** (or `--new-line`): Move braces to the condition line. |
| `--new-line` | **Required** (or `--same-line`): Move braces to the next line. |
| `--dry-run` | Shows changes to console without writing to files. |
| `--ext <ext>` | Filter by extension (e.g., `--ext c --ext h`). |
| `--exclude <dir>` | Ignore specific folders (default: `.git`, `build`, `out`). |

## 🛡 Safety and Edge Cases

The script is designed to skip formatting a single block if it detects ambiguous situations, such as:
- **Inline Comments (`//`)**: If a comment prevents moving a brace to the same line without "commenting it out", the script skips the change.
- **Complex Macros**: If non-recognized tokens (e.g., multi-line macros) appear between the parenthesis and brace, the block is skipped for safety.
- **Strings**: Braces inside strings (e.g., `printf("{");`) are never touched.

## 📄 License

Released under the MIT License.
```