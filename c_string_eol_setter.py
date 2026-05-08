#!/usr/bin/env python3
import argparse
import pathlib
import sys
import bisect


def get_newline_indices(text):
    """Pre-calculates indices of all newlines in the text."""
    return [i for i, c in enumerate(text) if c == '\n']


def fast_line_of_pos(newline_indices, pos):
    """Uses binary search to find the line number in O(log N) time."""
    return bisect.bisect_right(newline_indices, pos) + 1


def is_ident_start(c):
    return c.isalpha() or c == '_'


def is_ident_char(c):
    return c.isalnum() or c == '_'


def parse_string_literal(text, i):
    n = len(text)
    assert text[i] == '"'
    start = i
    i += 1
    content_start = i

    while i < n:
        c = text[i]
        if c == '\\':
            i += 2
            continue
        if c == '"':
            content_end = i
            return {
                'full_start': start,
                'content_start': content_start,
                'content_end': content_end,
                'full_end': i + 1,
            }
        i += 1

    return None


def skip_line_comment(text, i):
    n = len(text)
    while i < n and text[i] != '\n':
        i += 1
    return i


def skip_block_comment(text, i):
    n = len(text)
    i += 2
    while i + 1 < n:
        if text[i] == '*' and text[i + 1] == '/':
            return i + 2
        i += 1
    return n


def skip_char_literal(text, i):
    n = len(text)
    i += 1
    while i < n:
        if text[i] == '\\':
            i += 2
            continue
        if text[i] == '\'':
            return i + 1
        i += 1
    return n


def transform_escaped_newlines(s, mode):
    out = []
    i = 0
    changed = False
    n = len(s)

    while i < n:
        if s[i] == '\\':

            # --- HANDLE TYPO \n\r (LFCR) ---
            if i + 3 < n and s[i:i+4] == '\\n\\r':
                if mode == 'to-crlf':
                    out.extend(['\\', 'r', '\\', 'n'])
                elif mode == 'to-lf':
                    out.extend(['\\', 'n'])
                changed = True
                i += 4
                continue

            if mode == 'to-crlf':
                if i + 1 < n and s[i + 1] == 'n':
                    prev_is_r = (len(out) >= 2 and out[-2] == '\\' and out[-1] == 'r')
                    if prev_is_r:
                        out.append('\\')
                        out.append('n')
                    else:
                        out.extend(['\\', 'r', '\\', 'n'])
                        changed = True
                    i += 2
                    continue

            elif mode == 'to-lf':
                # Convert \r\n to \n
                if i + 3 < n and s[i:i+4] == '\\r\\n':
                    out.extend(['\\', 'n'])
                    changed = True
                    i += 4
                    continue
                # Convert standalone \r to \n
                if i + 1 < n and s[i + 1] == 'r':
                    out.extend(['\\', 'n'])
                    changed = True
                    i += 2
                    continue

            if i + 1 < n:
                out.append(s[i])
                out.append(s[i + 1])
                i += 2
            else:
                out.append(s[i])
                i += 1
            continue

        out.append(s[i])
        i += 1

    return ''.join(out), changed


def process_calls(text, mode, only_names=None, exclude_names=None):
    """
    Scans C/C++ text and transforms newline escapes in strings found inside
    function/macro calls corresponding to only_names.

    MAIN FIX: uses a call stack (call_stack) instead of just remembering the
    last identifier. This way a string inside usb_echo("...\r\n") nested in an
    if(...) is correctly attributed to usb_echo and not to if.

    exclude_names: set of function/macro names to explicitly ignore.
    """
    n = len(text)
    i = 0
    replacements = []
    planned = []
    matched_calls_total = 0

    newline_indices = get_newline_indices(text)

    # Stack of open identifiers: each element is the name of the function/
    # keyword whose '(' has not yet been closed by the corresponding ')'.
    # E.g: if ( usb_echo( "str" ) )
    #      ^--- depth 1      ^--- depth 2
    # call_stack = ['if', 'usb_echo']  when we are inside the string
    call_stack = []

    while i < n:
        c = text[i]

        # --- Comments ---
        if c == '/' and i + 1 < n:
            if text[i + 1] == '/':
                i = skip_line_comment(text, i + 2)
                continue
            if text[i + 1] == '*':
                i = skip_block_comment(text, i)
                continue

        # --- Character literal ---
        if c == '\'':
            i = skip_char_literal(text, i)
            continue

        # --- String literal ---
        if c == '"':
            s = parse_string_literal(text, i)
            if s is None:
                i += 1
                continue

            # Are we inside a call? The correct name is the top of the stack.
            if call_stack:
                current_func = call_stack[-1]
                included = (only_names is None or current_func in only_names)
                excluded = (exclude_names is not None and current_func in exclude_names)
                if included and not excluded:
                    original = text[s['content_start']:s['content_end']]
                    transformed, changed = transform_escaped_newlines(original, mode)
                    if changed:
                        replacements.append((s['content_start'], s['content_end'], transformed))
                        planned.append({
                            'func': current_func,
                            'line': fast_line_of_pos(newline_indices, s['full_start']),
                            'old': original,
                            'new': transformed,
                        })

            i = s['full_end']
            continue

        # --- Open parenthesis without preceding identifier ---
        # (e.g: cast, arithmetic expression)
        if c == '(':
            call_stack.append('')   # anonymous slot to maintain depth
            i += 1
            continue

        # --- Closing parenthesis: pop from stack ---
        if c == ')':
            if call_stack:
                popped = call_stack.pop()
                # Count as "call found" only if it was a real name
                if popped and (only_names is None or popped in only_names):
                    matched_calls_total += 1
            i += 1
            continue

        # --- Identifier ---
        if not is_ident_start(c):
            i += 1
            continue

        ident_start = i
        i += 1
        while i < n and is_ident_char(text[i]):
            i += 1
        ident = text[ident_start:i]

        # Skip spaces after identifier
        j = i
        while j < n and text[j].isspace():
            j += 1

        if j < n and text[j] == '(':
            # It's a call: push the name onto the stack
            call_stack.append(ident)
            i = j + 1          # skip the '('
        else:
            i = j              # simple identifier, advance

    # Apply replacements in order to avoid shifting indices
    if not replacements:
        return text, False, matched_calls_total, 0, planned

    parts = []
    last = 0
    for start, end, new_content in sorted(replacements, key=lambda x: x[0]):
        parts.append(text[last:start])
        parts.append(new_content)
        last = end
    parts.append(text[last:])
    new_text = ''.join(parts)

    return new_text, True, matched_calls_total, len(replacements), planned


def emit(line, report_lines=None, stream=None):
    if stream is not None:
        print(line, file=stream)
    else:
        print(line)
    if report_lines is not None:
        report_lines.append(line)


def iter_targets(root):
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
    """
    Checks only directory components, not the file name.
    Avoids false positives like 'build_tools/src/main.c' excluded for 'build'.
    """
    return any(part in exclude_set for part in path.parts[:-1])


def main():
    ap = argparse.ArgumentParser(
        description='Robustly converts \\n <-> \\r\\n escapes in strings inside C/C++ calls'
    )
    ap.add_argument('root', nargs='?', default='.', help='Root folder (default: current directory)')
    ap.add_argument('--dry-run', action='store_true',
                    help='Show only files that would change, without modifying them')
    ap.add_argument('--dry-run-output', type=pathlib.Path, default=None,
                    help='Save detailed dry-run report to a file')
    ap.add_argument('--ext', action='append', default=[],
                    help='Extension to include, e.g: .c, c, .h, cpp (repeatable)')
    ap.add_argument('--exclude', action='append',
                    default=['.git', 'build', 'out', 'output', '.idea', '.vscode'],
                    help='Directory names to exclude (repeatable)')
    ap.add_argument('--only-token', action='append', default=[], dest='only_token',
                    help='Limit to function/macro names only (repeatable); if omitted, all calls')
    ap.add_argument('--exclude-token', action='append', default=[], dest='exclude_token',
                    help='Explicitly exclude a function/macro name (repeatable), e.g: snprintf')
    ap.add_argument('--verbose', action='store_true',
                    help='Print details per file')

    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--to-crlf', action='store_true',
                       help='Converts \\n to \\r\\n (and \\n\\r to \\r\\n)')
    group.add_argument('--to-lf', action='store_true',
                       help='Converts \\r\\n to \\n (and \\n\\r to \\n, and standalone \\r to \\n)')

    args = ap.parse_args()

    mode = 'to-crlf' if args.to_crlf else 'to-lf'
    root = pathlib.Path(args.root)
    exts = {e if e.startswith('.') else f'.{e}' for e in args.ext}
    exts = {e.lower() for e in exts}
    only_names = set(args.only_token) if args.only_token else None
    exclude_token_set = set(args.exclude_token) if args.exclude_token else None
    exclude_set = set(args.exclude)

    scanned = 0
    read_ok = 0
    matched_calls_total = 0
    string_replacements_total = 0
    changed_files = []
    report_lines = []
    found_tokens = set()   # nomi di funzione/macro effettivamente incontrati

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
            text = path.read_text(encoding='utf-8')
            encoding = 'utf-8'
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding='latin-1')
                encoding = 'latin-1'
            except Exception:
                continue
        except Exception:
            continue

        read_ok += 1

        new_text, changed, matched_calls, replacements, planned = process_calls(text, mode, only_names, exclude_token_set)
        matched_calls_total += matched_calls
        string_replacements_total += replacements

        if planned:
            emit(f'\n=== {path} ===', report_lines)
            for item in planned:
                found_tokens.add(item['func'])
                emit(f"[line {item['line']}] {item['func']}", report_lines)
                emit(f"  OLD: {item['old']!r}", report_lines)
                emit(f"  NEW: {item['new']!r}", report_lines)

        if args.verbose and (matched_calls > 0 or replacements > 0):
            emit(f'{path} | call trovate: {matched_calls} | stringhe modificate: {replacements}', report_lines)

        if changed:
            changed_files.append(str(path))
            if not args.dry_run:
                path.write_text(new_text, encoding=encoding)

    tokens_str = ', '.join(sorted(found_tokens)) if found_tokens else '(none)'
    summary = [
        '',
        f'Files scanned:       {scanned}',
        f'Files read:          {read_ok}',
        f'Calls found:         {matched_calls_total}',
        f'Strings modified:    {string_replacements_total}',
        f'Files modified:      {len(changed_files)}',
        f'Tokens identified:   {tokens_str}',
    ]

    for line in summary:
        print(line, file=sys.stderr)
        report_lines.append(line)

    if args.dry_run_output:
        args.dry_run_output.parent.mkdir(parents=True, exist_ok=True)
        args.dry_run_output.write_text('\n'.join(report_lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
