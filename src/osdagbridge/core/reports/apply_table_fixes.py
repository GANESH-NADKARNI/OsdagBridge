"""
apply_table_fixes.py -- one-off codemod for the OsdagBridge report chapters.

Run from the reports directory (src/osdagbridge/core/reports):

    python apply_table_fixes.py --check     # dry run: report what would change
    python apply_table_fixes.py             # rewrite chap3.py chap5.py chap7.py

What it does
1. Every  \\begin{longtable}{..} [\\caption{\\textbf{T}}] \\hline HEADER \\hline
   gets \\endfirsthead / \\endhead blocks so the header repeats on every page
   (a "Table N (continued): T" caption is added on continuation pages).
2. In chap5, every  X.append( r"\\multirow{..." ... )  group is wrapped in
   keep_rows_together(...) so a girder block never splits across pages.

It is idempotent (safe to run twice) and preserves CRLF line endings.
Review the result with `git diff`.
"""
import re
import sys

FILES = ["chap3.py", "chap5.py", "chap7.py"]
IMPORT_LINE = "from osdagbridge.core.reports.latex_tables import keep_rows_together"

# Shape A:  \begin{longtable}{SPEC} / [\caption{T}] / \hline / HEADER ROW / \hline
_LT = re.compile(
    r"(?P<begin>\\begin\{longtable\}\{[^\n]*\}\n)"
    r"(?P<cap>\\caption\{(?P<title>[^\n]*)\}\n)?"
    r"\\hline\n"
    r"(?P<head>(?:(?!\"\"\")[^\n])*\\\\(?:\[[^\]]*\])?)\n"
    r"\\hline\n"
)
# Shape B:  caption + \hline and NO header row (the first line is already data;
# it may contain Python interpolation).  Only reached for tables Shape A skipped.
_LT_NOHEAD = re.compile(
    r"(?P<begin>\\begin\{longtable\}\{[^\n]*\}\n)"
    r"(?P<cap>\\caption\{(?P<title>[^\n]*)\}\n)"
    r"\\hline\n"
)


def _plain_title(title):
    """'\\textbf{X}' -> 'X'; plain 'X' stays 'X'."""
    m = re.fullmatch(r"\\textbf\{(.*)\}", title)
    return m.group(1) if m else title


def _converted_flags(src):
    """For each longtable, True if it already has \\endhead before its end."""
    flags, pos = [], 0
    while True:
        i = src.find("\\begin{longtable}", pos)
        if i < 0:
            return flags
        j = src.find("\\end{longtable}", i)
        flags.append("\\endhead" in src[i:j if j >= 0 else len(src)])
        pos = i + 1


def _fix_longtables(src):
    before = sum(_converted_flags(src))

    def repl_a(m):
        # A match must be an unconverted table: converted ones have "\\\\" after
        # the caption, which this pattern cannot match.
        head = m.group("head")
        block = "\\hline\n" + head + "\n\\hline\n"
        if m.group("cap"):
            t = _plain_title(m.group("title"))
            return (m.group("begin")
                    + "\\caption{" + m.group("title") + "}\\\\\n"
                    + block + "\\endfirsthead\n"
                    + "\\caption*{\\textbf{Table \\thetable{} (continued): " + t + "}}\\\\\n"
                    + block + "\\endhead\n")
        return m.group("begin") + block + "\\endhead\n"  # no caption (Table 7.1)

    def repl_b(m):
        t = _plain_title(m.group("title"))
        return (m.group("begin")
                + "\\caption{" + m.group("title") + "}\\\\\n"
                + "\\hline\n\\endfirsthead\n"
                + "\\caption*{\\textbf{Table \\thetable{} (continued): " + t + "}}\\\\\n"
                + "\\hline\n\\endhead\n")

    src = _LT.sub(repl_a, src)
    src = _LT_NOHEAD.sub(repl_b, src)
    flags = _converted_flags(src)
    return src, len(flags), sum(flags) - before, before


_APPEND = re.compile(r"^(?P<ind>[ \t]*)(?P<var>\w+)\.append\(\n(?P=ind)[ \t]+r\"\\multirow", re.M)


def _wrap_multirow_groups(src):
    lines = src.split("\n")
    out, i, wrapped = [], 0, 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([ \t]*)(\w+)\.append\($", line)
        if (m and i + 1 < len(lines)
                and re.match(r'^[ \t]+r"\\multirow', lines[i + 1])):
            ind = m.group(1)
            # find the closing ")" at the same indent
            j = i + 1
            while j < len(lines) and lines[j].rstrip() != ind + ")":
                j += 1
            if j < len(lines) and "keep_rows_together(" not in line:
                out.append(ind + m.group(2) + ".append(keep_rows_together(")
                out.extend(lines[i + 1:j])
                out.append(ind + "))")
                wrapped += 1
                i = j + 1
                continue
        out.append(line)
        i += 1
    return "\n".join(out), wrapped


def _add_import(src):
    if IMPORT_LINE in src:
        return src
    m = re.search(r"^from osdagbridge\.core\.reports\.report_utils import[^\n]*\n", src, re.M)
    if m:
        return src[:m.end()] + IMPORT_LINE + "\n" + src[m.end():]
    return IMPORT_LINE + "\n" + src


def process(path, check):
    raw = open(path, "rb").read().decode("utf-8")
    crlf = "\r\n" in raw
    src = raw.replace("\r\n", "\n")

    src, n_total, done, skipped = _fix_longtables(src)
    unconverted = n_total - done - skipped
    wrapped = 0
    if path.endswith("chap5.py"):
        src, wrapped = _wrap_multirow_groups(src)
        if wrapped:
            src = _add_import(src)

    print("%-10s longtables: %2d | headers added: %2d | already done: %d | "
          "multirow groups wrapped: %d" % (path, n_total, done, skipped, wrapped))
    if unconverted:
        print("   !! %d longtable(s) did not match any template; convert by hand" % unconverted)
    if not check and (done or wrapped):
        out = src.replace("\n", "\r\n") if crlf else src
        open(path, "wb").write(out.encode("utf-8"))


if __name__ == "__main__":
    check = "--check" in sys.argv
    for f in FILES:
        process(f, check)
    print("(dry run, nothing written)" if check else "done")
