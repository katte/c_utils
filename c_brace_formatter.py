#!/usr/bin/env python3
import argparse
import pathlib
import sys
import bisect

def get_newline_indices(text):
    return [i for i, c in enumerate(text) if c == '\n']

def fast_line_of_pos(newline_indices, pos):
    return bisect.bisect_right(newline_indices, pos) + 1

def is_ident_start(c):
    return c.isalpha() or c == '_'

def is_ident_char(c):
    return c.isalnum() or c == '_'

def get_indent(text, pos):
    """Calculates the indentation of the line to which 'pos' belongs."""
    line_start = text.rfind('\n', 0, pos)
    line_start = line_start + 1 if line_start != -1 else 0
    indent = []
    for i in range(line_start, pos):
        if text[i] in ' \t':
            indent.append(text[i])
        else:
            break
    return ''.join(indent)

def tokenize(text):
    """Lexical analyzer that converts text into tokens for safe scanning."""
    tokens = []
    n = len(text)
    i = 0
    while i < n:
        c = text[i]
        if c.isspace():
            start = i
            while i < n and text[i].isspace(): i += 1
            tokens.append(('WS', start, i))
        elif c == '"':
            start = i; i += 1
            while i < n:
                if text[i] == '\\': i += 2
                elif text[i] == '"': i += 1; break
                else: i += 1
            tokens.append(('STRING', start, min(i, n)))
        elif c == "'":
            start = i; i += 1
            while i < n:
                if text[i] == '\\': i += 2
                elif text[i] == "'": i += 1; break
                else: i += 1
            tokens.append(('CHAR', start, min(i, n)))
        elif c == '/' and i + 1 < n and text[i+1] == '/':
            start = i; i += 2
            while i < n and text[i] != '\n': i += 1
            tokens.append(('LINE_COMMENT', start, i))
        elif c == '/' and i + 1 < n and text[i+1] == '*':
            start = i; i += 2
            while i + 1 < n and not (text[i] == '*' and text[i+1] == '/'): i += 1
            i += 2
            tokens.append(('BLOCK_COMMENT', start, min(i, n)))
        elif c == '(':
            tokens.append(('LPAREN', i, i+1)); i += 1
        elif c == ')':
            tokens.append(('RPAREN', i, i+1)); i += 1
        elif c == '{':
            tokens.append(('LBRACE', i, i+1)); i += 1
        elif c == '}':
            tokens.append(('RBRACE', i, i+1)); i += 1
        elif is_ident_start(c):
            start = i
            while i < n and is_ident_char(text[i]): i += 1
            ident = text[start:i]
            # Also handles for/while/switch since the structure is identical to if()
            if ident in ('if', 'for', 'while', 'switch'): tokens.append(('CTRL_PAREN', start, i))
            elif ident == 'else': tokens.append(('ELSE', start, i))
            else: tokens.append(('IDENT', start, i))
        else:
            tokens.append(('OTHER', i, i+1)); i += 1
    return tokens

def generate_replacement(text, gap_start, gap_end, indent, mode):
    """Calculates the new content of the space between the keyword and the brace."""
    gap_tokens = tokenize(text[gap_start:gap_end])

    # If the gap contains unexpected garbage (e.g. multi-line macro with '\'), don't touch it
    if any(t[0] not in ('WS', 'LINE_COMMENT', 'BLOCK_COMMENT') for t in gap_tokens):
        return None

    has_line_comment = any(t[0] == 'LINE_COMMENT' for t in gap_tokens)
    has_block_comment = any(t[0] == 'BLOCK_COMMENT' for t in gap_tokens)
    nl = '\r\n' if '\r\n' in text else '\n'

    if mode == 'same-line':
        # If there's a // comment, moving the brace to the same line would comment it out! Better skip.
        if has_line_comment: return None
        if not has_block_comment: return " "

        res = " "
        for t in gap_tokens:
            if t[0] == 'BLOCK_COMMENT':
                res += text[gap_start+t[1]:gap_start+t[2]] + " "
        return res

    elif mode == 'new-line':
        if not gap_tokens:
            return nl + indent

        comments = [text[gap_start+t[1]:gap_start+t[2]] for t in gap_tokens if t[0] in ('LINE_COMMENT', 'BLOCK_COMMENT')]
        if not comments:
            return nl + indent

        out = " "
        for i, c in enumerate(comments):
            out += c
            if c.startswith('//'): out += nl + indent
            else:
                if i == len(comments) - 1: out += nl + indent
                else: out += " "
        return out

def process_braces(text, mode):
    tokens = tokenize(text)
    # Filter only significant tokens to find the logic
    sig_tokens = [(idx, t) for idx, t in enumerate(tokens) if t[0] not in ('WS', 'LINE_COMMENT', 'BLOCK_COMMENT')]

    replacements = []
    planned = []
    newline_indices = get_newline_indices(text)
    matched_cases = 0

    for i, (orig_idx, token) in enumerate(sig_tokens):
        # 1. Find pattern: if (...) {
        if token[0] == 'CTRL_PAREN':
            if i + 1 < len(sig_tokens) and sig_tokens[i+1][1][0] == 'LPAREN':
                depth = 1
                rparen_idx = -1
                for j in range(i + 2, len(sig_tokens)):
                    if sig_tokens[j][1][0] == 'LPAREN': depth += 1
                    elif sig_tokens[j][1][0] == 'RPAREN':
                        depth -= 1
                        if depth == 0:
                            rparen_idx = j
                            break
                if rparen_idx != -1 and rparen_idx + 1 < len(sig_tokens):
                    if sig_tokens[rparen_idx+1][1][0] == 'LBRACE':
                        gap_start = sig_tokens[rparen_idx][1][2]
                        gap_end = sig_tokens[rparen_idx+1][1][1]
                        indent = get_indent(text, token[1])
                        new_gap = generate_replacement(text, gap_start, gap_end, indent, mode)
                        if new_gap is not None and new_gap != text[gap_start:gap_end]:
                            matched_cases += 1
                            replacements.append((gap_start, gap_end, new_gap))
                            planned.append({'func': f"{text[token[1]:token[2]]} (...) {{", 'line': fast_line_of_pos(newline_indices, gap_start), 'old': text[gap_start:gap_end], 'new': new_gap})

        # 2. Find pattern: } else {
        elif token[0] == 'ELSE':
            # Check backward for '}' -> 'else'
            if i - 1 >= 0 and sig_tokens[i-1][1][0] == 'RBRACE':
                gap_start = sig_tokens[i-1][1][2]
                gap_end = token[1]
                indent = get_indent(text, sig_tokens[i-1][1][1])
                new_gap = generate_replacement(text, gap_start, gap_end, indent, mode)
                if new_gap is not None and new_gap != text[gap_start:gap_end]:
                    matched_cases += 1
                    replacements.append((gap_start, gap_end, new_gap))
                    planned.append({'func': "} else", 'line': fast_line_of_pos(newline_indices, gap_start), 'old': text[gap_start:gap_end], 'new': new_gap})

            # Check forward for 'else' -> '{' or 'else if'
            if i + 1 < len(sig_tokens):
                next_token = sig_tokens[i+1][1]
                if next_token[0] == 'LBRACE':
                    gap_start = token[2]
                    gap_end = next_token[1]
                    indent = get_indent(text, token[1])
                    new_gap = generate_replacement(text, gap_start, gap_end, indent, mode)
                    if new_gap is not None and new_gap != text[gap_start:gap_end]:
                        matched_cases += 1
                        replacements.append((gap_start, gap_end, new_gap))
                        planned.append({'func': "else {", 'line': fast_line_of_pos(newline_indices, gap_start), 'old': text[gap_start:gap_end], 'new': new_gap})

                # Special handling for 'else if' (always joined by 1 space)
                elif next_token[0] == 'CTRL_PAREN' and text[next_token[1]:next_token[2]] == 'if':
                    gap_start = token[2]
                    gap_end = next_token[1]
                    gap_text = text[gap_start:gap_end]
                    gap_tokens = tokenize(gap_text)
                    if not any(t[0] in ('LINE_COMMENT', 'BLOCK_COMMENT', 'OTHER') for t in gap_tokens):
                        new_gap = " "
                        if new_gap != gap_text:
                            matched_cases += 1
                            replacements.append((gap_start, gap_end, new_gap))
                            planned.append({'func': "else if", 'line': fast_line_of_pos(newline_indices, gap_start), 'old': gap_text, 'new': new_gap})

    if not replacements:
        return text, False, matched_cases, 0, planned

    parts = []
    last = 0
    for start, end, new_content in sorted(replacements, key=lambda x: x[0]):
        parts.append(text[last:start])
        parts.append(new_content)
        last = end
    parts.append(text[last:])
    
    return ''.join(parts), True, matched_cases, len(replacements), planned

def emit(line, report_lines=None, stream=None):
    if stream is not None:
        print(line, file=stream)
    else:
        print(line)
    if report_lines is not None:
        report_lines.append(line)


def iter_targets(root):
    # Glob pattern: if the path contains * or ?, expand from the parent directory
    root_str = str(root)
    if '*' in root_str or '?' in root_str:
        parent = root.parent
        pattern = root.name
        if not parent.is_dir():
            raise FileNotFoundError(f'Directory not found: {parent}')
        for match in sorted(parent.glob(pattern)):
            if match.is_file():
                yield match
            elif match.is_dir():
                yield from match.rglob('*')
        return
    if not root.exists():
        raise FileNotFoundError(f'Path not found: {root}')
    if root.is_file():
        yield root
        return
    if root.is_dir():
        yield from root.rglob('*')
        return
    raise ValueError(f'Path not supported: {root}')


def is_excluded(path, exclude_set):
    return any(part in exclude_set for part in path.parts[:-1])


def main():
    ap = argparse.ArgumentParser(description='Formats braces for if/else/for/while in C/C++')
    ap.add_argument('root', nargs='?', default='.', help='Single file or root folder (default: current directory)')
    ap.add_argument('--dry-run', action='store_true',
                    help='Show only files that would change, without modifying them')
    ap.add_argument('--dry-run-output', type=pathlib.Path, default=None,
                    help='Save detailed dry-run report to a file')
    ap.add_argument('--ext', action='append', default=[],
                    help='Extension to include, e.g: .c, c, .h, cpp (repeatable)')
    ap.add_argument('--exclude', action='append', default=['.git', 'build', 'out', 'output'],
                    help='Directory names to exclude (repeatable)')

    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--same-line', action='store_true', help='Format as: if () { ... } else {')
    group.add_argument('--new-line', action='store_true', help='Format as: if ()\\n{ ... }\\nelse\\n{')

    args = ap.parse_args()
    mode = 'same-line' if args.same_line else 'new-line'
    root = pathlib.Path(args.root)
    exts = {e.lower() if e.startswith('.') else f'.{e.lower()}' for e in args.ext}
    exclude_set = set(args.exclude)

    scanned = 0
    changed_files = []
    report_lines = []

    try:
        targets = iter_targets(root)
    except (FileNotFoundError, ValueError) as e:
        ap.error(str(e))

    for path in targets:
        if not path.is_file():
            continue
        if is_excluded(path, exclude_set):
            continue
        if exts and path.suffix.lower() not in exts:
            continue

        scanned += 1

        try:
            encoding = 'utf-8'
            text = path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            try:
                encoding = 'latin-1'
                text = path.read_text(encoding=encoding)
            except Exception:
                continue
        except Exception:
            continue

        new_text, changed, _, _, planned = process_braces(text, mode)

        if planned:
            emit(f'\n=== {path} ===', report_lines)
            for p in planned:
                disp_old = p['old'].replace('\n', '\\n').replace('\r', '\\r')
                disp_new = p['new'].replace('\n', '\\n').replace('\r', '\\r')
                emit(f"[line {p['line']}] {p['func']}: '{disp_old}' -> '{disp_new}'", report_lines)

        if changed:
            changed_files.append(str(path))
            if not args.dry_run:
                path.write_text(new_text, encoding=encoding)

    summary = [
        '',
        f'Files scanned:   {scanned}',
        f'Files modified:  {len(changed_files)}',
    ]
    for line in summary:
        print(line, file=sys.stderr)
        report_lines.append(line)

    if args.dry_run_output:
        args.dry_run_output.parent.mkdir(parents=True, exist_ok=True)
        args.dry_run_output.write_text('\n'.join(report_lines) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
    