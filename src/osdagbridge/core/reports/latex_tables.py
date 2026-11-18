"""
latex_tables.py -- table builders for the OsdagBridge report.

longtable()            one call replaces the repeated
                       \\begin{longtable} / \\caption / \\hline / header boilerplate
                       and adds \\endfirsthead / \\endhead so the column header
                       repeats on every page.
keep_rows_together()   forbids a page break inside a multirow group (for
                       example one girder's block of rows).  Without it the
                       group label (e.g. "G4") can be typeset on one page
                       while its rows continue on the next, which is what makes
                       the label collide with the footer.

All spacing values come from styles.TABLE.
"""
import re

from osdagbridge.core.reports import styles

# A row terminator is "\\" with an optional [length], at the END of a line.
# "\\" inside \makecell{A\\B} is not followed by a newline, so it is left alone.
MAX_SHORT_ROWS = 14   # above this, callers should use longtable() so the table can break

_ROW_END = re.compile(r"\\\\(\[[^\]]*\])?(?=[ \t]*\r?\n)")


def keep_rows_together(block):
    """Return `block` with page breaks forbidden between its rows.

    Every row terminator except the last becomes ``\\\\*`` (longtable's
    "no break after this row").  The last row stays breakable, so the group
    can still be followed by a page break.
    """
    matches = list(_ROW_END.finditer(block))
    if len(matches) < 2:
        return block
    out, last = [], 0
    for m in matches[:-1]:
        out.append(block[last:m.start()])
        out.append("\\\\*" + (m.group(1) or ""))
        last = m.end()
    out.append(block[last:])
    # \cline is its own alignment row followed by a \vskip, which is a legal
    # break point; \kcline (defined in the preamble) forbids it.
    text = re.sub(r"\\cline\{", lambda _m: "\\kcline{", "".join(out))
    # A rule (\hline) is followed by glue, another legal break point that \\*
    # cannot reach: add a no-break penalty after every \hline that follows a
    # starred row terminator.
    return re.sub(r"(\\\\\*(?:\[[^\]]*\])?[ \t]*\r?\n\\hline)",
                  lambda m: m.group(1) + "\\noalign{\\penalty10000}", text)


def _header_row(header):
    """Accept a ready-made row string or a list of cell labels."""
    if isinstance(header, (list, tuple)):
        return " & ".join(r"\textbf{" + str(c) + "}" for c in header)
    return header


def longtable(colspec, caption, header, body, note=None, *, repeat_header=None):
    """Build a longtable whose header row repeats on every page.

    Parameters
    ----------
    colspec : str     column specification, e.g. ``|C{2.5cm}|L{8cm}|``
    caption : str     table title (plain LaTeX; wrapped in \\textbf)
    header  : str|list header row (without trailing ``\\\\``) or list of labels
    body    : str     already-built rows, each ending in ``\\\\`` + ``\\hline``
    note    : str     optional italic note printed under the table
    """
    if repeat_header is None:
        repeat_header = styles.TABLE["repeat_header"]
    gap = styles.TABLE["row_gap"]
    head = _header_row(header)
    head_block = "\\hline\n" + head + " \\\\[" + gap + "]\n\\hline\n"

    parts = [
        "\\begin{longtable}{" + colspec + "}",
        "\\caption{\\textbf{" + caption + "}}\\\\",
        head_block + ("\\endfirsthead" if repeat_header else ""),
    ]
    if repeat_header:
        parts += [
            # \caption* keeps the table number unchanged on continuation pages
            "\\caption*{\\textbf{Table \\thetable{} (continued): " + caption + "}}\\\\",
            head_block + "\\endhead",
        ]
    parts.append(body)
    parts.append("\\end{longtable}")
    if note:
        parts.append("\\noindent\\textit{" + note + "}\\par\\vspace{0.6em}")
    return "\n".join(parts) + "\n"


def short_table(colspec, caption, header, body, note=None):
    """A table that can never split across pages (use for short tables).

    longtable paginates itself and ignores \\\\* / penalty hints between rows
    that are separated by \\hline, so a few-row longtable can still be cut.
    A tabular inside a minipage is one unbreakable box: if it does not fit on
    the page it moves to the next page as a whole.  The caption is numbered
    from the same counter as longtable captions.
    """
    gap = styles.TABLE["row_gap"]
    parts = [
        "\\par\\vspace{0.4em}\\noindent\\begin{minipage}{\\linewidth}",
        "\\captionof{table}{\\textbf{" + caption + "}}",
        "\\centering",
        "\\begin{tabular}{" + colspec + "}",
        "\\hline",
        _header_row(header) + " \\\\[" + gap + "]",
        "\\hline",
        body.rstrip("\n"),
        "\\end{tabular}",
    ]
    if note:   # inside the box, so the note can never be separated from its table
        parts.append("\\par\\vspace{0.4em}\\raggedright\\textit{" + note + "}")
    parts.append("\\end{minipage}\\par\\vspace{0.6em}")
    return "\n".join(parts) + "\n"