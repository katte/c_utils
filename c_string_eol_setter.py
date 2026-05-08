#!/usr/bin/env python3
import argparse
import pathlib
import sys
import bisect


def get_newline_indices(text):
    """Pre-calcola gli indici di tutti i newline nel testo."""
    return [i for i, c in enumerate(text) if c == '\n']


def fast_line_of_pos(newline_indices, pos):
    """Usa la ricerca binaria per trovare la riga in tempo O(log N)."""
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

            # --- GESTIONE TYPO \n\r (LFCR) ---
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
                # Converte \r\n in \n
                if i + 3 < n and s[i:i+4] == '\\r\\n':
                    out.extend(['\\', 'n'])
                    changed = True
                    i += 4
                    continue
                # Converte \r isolato in \n
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
    Scansiona il testo C/C++ e trasforma gli escape di newline nelle stringhe
    che si trovano dentro chiamate a funzione/macro corrispondenti a only_names.

    FIX PRINCIPALE: usa uno stack delle chiamate (call_stack) invece di
    ricordare solo l'ultimo identificatore. In questo modo una stringa dentro
    usb_echo("...\r\n") annidato in un if(...) viene attribuita correttamente
    a usb_echo e non a if.

    exclude_names: insieme di nomi di funzione/macro da ignorare esplicitamente.
    """
    n = len(text)
    i = 0
    replacements = []
    planned = []
    matched_calls_total = 0

    newline_indices = get_newline_indices(text)

    # Stack degli identificatori aperti: ogni elemento è il nome della funzione/
    # keyword il cui '(' non è ancora stato chiuso dal ')' corrispondente.
    # Es: if ( usb_echo( "str" ) )
    #      ^--- depth 1      ^--- depth 2
    # call_stack = ['if', 'usb_echo']  quando siamo dentro la stringa
    call_stack = []

    while i < n:
        c = text[i]

        # --- Commenti ---
        if c == '/' and i + 1 < n:
            if text[i + 1] == '/':
                i = skip_line_comment(text, i + 2)
                continue
            if text[i + 1] == '*':
                i = skip_block_comment(text, i)
                continue

        # --- Char literal ---
        if c == '\'':
            i = skip_char_literal(text, i)
            continue

        # --- String literal ---
        if c == '"':
            s = parse_string_literal(text, i)
            if s is None:
                i += 1
                continue

            # Siamo dentro una chiamata? Il nome corretto è il top dello stack.
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

        # --- Parentesi aperta senza identificatore precedente ---
        # (es: cast, espressione aritmetica)
        if c == '(':
            call_stack.append('')   # slot anonimo per mantenere il depth
            i += 1
            continue

        # --- Parentesi chiusa: pop dello stack ---
        if c == ')':
            if call_stack:
                popped = call_stack.pop()
                # Conta come "call trovata" solo se era un nome reale
                if popped and (only_names is None or popped in only_names):
                    matched_calls_total += 1
            i += 1
            continue

        # --- Identificatore ---
        if not is_ident_start(c):
            i += 1
            continue

        ident_start = i
        i += 1
        while i < n and is_ident_char(text[i]):
            i += 1
        ident = text[ident_start:i]

        # Salta spazi dopo l'identificatore
        j = i
        while j < n and text[j].isspace():
            j += 1

        if j < n and text[j] == '(':
            # È una chiamata: push del nome nello stack
            call_stack.append(ident)
            i = j + 1          # salta la '('
        else:
            i = j              # identificatore semplice, avanza

    # Applica le sostituzioni in ordine per non spostare gli indici
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
        raise FileNotFoundError(f'Percorso non trovato: {root}')
    if root.is_file():
        yield root
        return
    if root.is_dir():
        yield from root.rglob('*')
        return
    raise ValueError(f'Percorso non supportato: {root}')


def is_excluded(path, exclude_set):
    """
    Controlla solo le componenti di directory, non il nome del file.
    Evita falsi positivi tipo 'build_tools/src/main.c' escluso per 'build'.
    """
    return any(part in exclude_set for part in path.parts[:-1])


def main():
    ap = argparse.ArgumentParser(
        description='Converte in modo robusto gli escape \\n <-> \\r\\n nelle stringhe dentro call C/C++'
    )
    ap.add_argument('root', nargs='?', default='.', help='Cartella radice (default: directory corrente)')
    ap.add_argument('--dry-run', action='store_true',
                    help='Mostra solo i file che cambierebbero, senza modificarli')
    ap.add_argument('--dry-run-output', type=pathlib.Path, default=None,
                    help='Salva il report dettagliato del dry-run in un file')
    ap.add_argument('--ext', action='append', default=[],
                    help='Estensione da includere, es: .c, c, .h, cpp (ripetibile)')
    ap.add_argument('--exclude', action='append',
                    default=['.git', 'build', 'out', 'output', '.idea', '.vscode'],
                    help='Nomi di directory da escludere (ripetibile)')
    ap.add_argument('--only-token', action='append', default=[], dest='only_token',
                    help='Limita ai soli nomi funzione/macro (ripetibile); se omesso, tutte le call')
    ap.add_argument('--exclude-token', action='append', default=[], dest='exclude_token',
                    help='Esclude esplicitamente un nome funzione/macro (ripetibile), es: snprintf')
    ap.add_argument('--verbose', action='store_true',
                    help='Stampa dettagli per file')

    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--to-crlf', action='store_true',
                       help='Converte \\n in \\r\\n (e \\n\\r in \\r\\n)')
    group.add_argument('--to-lf', action='store_true',
                       help='Converte \\r\\n in \\n (e \\n\\r in \\n, e \\r isolato in \\n)')

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

    tokens_str = ', '.join(sorted(found_tokens)) if found_tokens else '(nessuno)'
    summary = [
        '',
        f'File scanditi:       {scanned}',
        f'File letti:          {read_ok}',
        f'Call trovate:        {matched_calls_total}',
        f'Stringhe modificate: {string_replacements_total}',
        f'File modificati:     {len(changed_files)}',
        f'Token individuati:   {tokens_str}',
    ]

    for line in summary:
        print(line, file=sys.stderr)
        report_lines.append(line)

    if args.dry_run_output:
        args.dry_run_output.parent.mkdir(parents=True, exist_ok=True)
        args.dry_run_output.write_text('\n'.join(report_lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
