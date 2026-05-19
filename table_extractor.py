from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ParsedTable:
    columns: list[str]
    rows: list[list[str]]
    source: str = ""


_NUM_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def decode_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def split_columns_spec(spec: str) -> list[str]:
    if not spec:
        return []
    parts: list[str] = []
    for chunk in re.split(r"[,\n\r;，；]+", spec):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts.extend([p for p in re.split(r"\s+", chunk) if p.strip()])
    return parts


def _normalize_col(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()


_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "frequency": ("freq(hz)", "freq"),
    "zreal": ("z'(a)", "zre"),
    "z real": ("z'(a)", "zre"),
    "zre": ("z'(a)", "zreal"),
    "zimag": ("z''(b)", "zim"),
    "z imag": ("z''(b)", "zim"),
    "zim": ("z''(b)", "zimag"),
}


def _candidate_column_names(requested: str) -> list[str]:
    req_norm = _normalize_col(requested)
    candidates = [req_norm, *_COLUMN_ALIASES.get(req_norm, ())]
    out: list[str] = []
    seen: set[str] = set()
    for name in candidates:
        norm = _normalize_col(name)
        if norm and norm not in seen:
            out.append(norm)
            seen.add(norm)
    return out


def _pick_columns(all_columns: Sequence[str], requested: Sequence[str]) -> list[int]:
    if not requested:
        return list(range(len(all_columns)))

    norm_to_index: dict[str, int] = {_normalize_col(c): i for i, c in enumerate(all_columns)}
    picked: list[int] = []

    for req in requested:
        req_norm = _normalize_col(req)
        if not req_norm:
            continue

        for candidate in _candidate_column_names(req):
            if candidate in norm_to_index:
                picked.append(norm_to_index[candidate])
                break
        else:
            matches = [
                i
                for i, col in enumerate(all_columns)
                if req_norm in _normalize_col(col)
            ]
            if len(matches) == 1:
                picked.append(matches[0])
                continue
            if not matches:
                raise ValueError(f"找不到列: {req!r}，可用列: {', '.join(all_columns)}")
            raise ValueError(
                f"列名 {req!r} 匹配到多个列: {', '.join(all_columns[i] for i in matches)}；请更精确"
            )

    return picked


def parse_dta_first_table(text: str, *, table_key: Optional[str] = None) -> ParsedTable:
    lines = text.splitlines()

    table_line_index: Optional[int] = None
    if table_key:
        key = table_key.strip()
        for i, line in enumerate(lines):
            if line.strip() == f"{key}\tTABLE":
                table_line_index = i
                break

    if table_line_index is None:
        for i, line in enumerate(lines):
            if "\tTABLE" in line:
                table_line_index = i
                break

    if table_line_index is None:
        raise ValueError("未找到 DTA 的 TABLE 区段（例如 'ZCURVE\\tTABLE'）")

    i = table_line_index + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        raise ValueError("TABLE 区段后缺少表头行")

    header_cols = [c.strip() for c in lines[i].split("\t") if c.strip()]
    if not header_cols:
        raise ValueError("表头行为空")

    # 下一行通常是单位行（# / s / Hz / ohm / ...），跳过
    i += 2

    rows: list[list[str]] = []
    expected = len(header_cols)
    while i < len(lines):
        raw = lines[i]
        if not raw.strip():
            if rows:
                break
            i += 1
            continue

        parts = [p.strip() for p in raw.split("\t") if p.strip() != ""]
        if len(parts) < expected:
            break

        if not _NUM_RE.match(parts[0]):
            break

        rows.append(parts[:expected])
        i += 1

    if not rows:
        raise ValueError("未解析到数据行")

    return ParsedTable(columns=header_cols, rows=rows, source="dta")


def parse_delimited_text(text: str, *, delimiter: Optional[str] = None) -> ParsedTable:
    sample = text[:8192]
    if delimiter is None:
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", "\t", ";", "|"])
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = "\t" if "\t" in sample else ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise ValueError("文件为空或未识别到表格内容")

    columns = [c.strip() for c in rows[0]]
    data_rows = [[c.strip() for c in r] for r in rows[1:]]
    if not columns:
        raise ValueError("未识别到表头行")

    return ParsedTable(columns=columns, rows=data_rows, source="delimited")


def _split_tab_columns(line: str) -> list[str]:
    return [c.strip() for c in line.strip().split("\t") if c.strip()]


def parse_multistat_data_file(text: str) -> ParsedTable:
    lines = text.splitlines()

    header_line_index: Optional[int] = None
    for marker in ("AC File Columns", "DC File Columns"):
        marker_index: Optional[int] = None
        for i, line in enumerate(lines):
            if marker in line:
                marker_index = i
                break
        if marker_index is None:
            continue

        for i in range(marker_index + 1, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("End Information:"):
                break
            cols = _split_tab_columns(lines[i])
            if len(cols) > 1:
                header_line_index = i
        if header_line_index is not None:
            break

    if header_line_index is None:
        for i, line in enumerate(lines):
            cols = _split_tab_columns(line)
            if len(cols) > 1 and not _NUM_RE.match(cols[0]):
                header_line_index = i

    if header_line_index is None:
        raise ValueError("未找到 MultiStat 数据列头")

    header_cols = _split_tab_columns(lines[header_line_index])
    if not header_cols:
        raise ValueError("MultiStat 数据列头为空")

    data_start = header_line_index + 1
    for i in range(header_line_index + 1, len(lines)):
        if lines[i].strip().startswith("End Header:"):
            data_start = i + 1
            break

    rows: list[list[str]] = []
    expected = len(header_cols)
    for i in range(data_start, len(lines)):
        raw = lines[i]
        if not raw.strip():
            if rows:
                break
            continue

        parts = _split_tab_columns(raw)
        if len(parts) < expected:
            if rows:
                break
            continue

        if not _NUM_RE.match(parts[0]):
            if rows:
                break
            continue

        rows.append(parts[:expected])

    if not rows:
        raise ValueError("未解析到 MultiStat 数据行")

    return ParsedTable(columns=header_cols, rows=rows, source="multistat")


def _score_mdat_entry(name: str, text: str) -> int:
    suffix = Path(name).suffix.lower()
    score = 0
    if suffix == ".z":
        score += 1000
    if "MultiStat_ACData" in text:
        score += 500
    if "AC File Columns" in text:
        score += 300
    if re.search(r"Exp Name:\s+Impedance\b", text):
        score += 100
    if re.search(r"Z\d+\s+Name:\s+Main\b", text):
        score += 20
    if "Step2" in text:
        score += 5
    if suffix == ".cor":
        score += 1
    return score


def parse_mdat_first_ac_table(data: bytes) -> ParsedTable:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ValueError(".mdat 文件不是有效的 zip 容器") from e

    candidates: list[tuple[int, int, str, ParsedTable]] = []
    errors: list[str] = []
    with archive:
        for order, info in enumerate(archive.infolist()):
            if info.is_dir():
                continue
            name = info.filename
            suffix = Path(name).suffix.lower()
            if suffix not in {".z", ".cor", ".txt", ".dat"}:
                continue

            raw = archive.read(info)
            text = decode_text(raw)
            if "File Columns" not in text or "End Header:" not in text:
                continue

            try:
                table = parse_multistat_data_file(text)
            except Exception as e:
                errors.append(f"{name}: {e}")
                continue

            score = _score_mdat_entry(name, text)
            candidates.append((score, -order, name, table))

    if not candidates:
        extra = f"；尝试过的区段: {'; '.join(errors)}" if errors else ""
        raise ValueError(f"未在 .mdat 中找到可解析的 AC/EIS 数据集（通常是 .z 文件）{extra}")

    _score, _order, name, table = max(candidates, key=lambda item: (item[0], item[1]))
    return ParsedTable(columns=table.columns, rows=table.rows, source=f"mdat:{name}")


def parse_table_from_bytes(filename: str, data: bytes) -> ParsedTable:
    ext = Path(filename).suffix.lower()

    if ext == ".mdat":
        return parse_mdat_first_ac_table(data)

    text = decode_text(data)

    if ext == ".dta":
        return parse_dta_first_table(text)

    if ext in {".z", ".cor"}:
        return parse_multistat_data_file(text)

    return parse_delimited_text(text)


def read_file_bytes(path: Path | str) -> tuple[str, bytes]:
    p = Path(path)
    return p.name, p.read_bytes()


def extract_table(
    table: ParsedTable,
    *,
    columns: Sequence[str],
    start_row: int = 1,
    end_row: Optional[int] = None,
    max_rows: Optional[int] = None,
    row_keyword: Optional[str] = None,
) -> ParsedTable:
    if start_row < 1:
        raise ValueError("start_row 必须 >= 1（数据行从 1 开始计数）")

    picked_idx = _pick_columns(table.columns, columns)

    filtered = table.rows
    if row_keyword and row_keyword.strip():
        kw = row_keyword.strip().lower()
        filtered = [r for r in filtered if any(kw in (c or "").lower() for c in r)]

    start0 = start_row - 1
    if end_row is not None and end_row < start_row:
        raise ValueError("end_row 不能小于 start_row")

    if end_row is None and max_rows is not None:
        end_row = start_row + max_rows - 1

    end0_exclusive = len(filtered) if end_row is None else min(len(filtered), end_row)
    sliced = filtered[start0:end0_exclusive]

    new_columns = [table.columns[i] for i in picked_idx]
    new_rows = [[row[i] if i < len(row) else "" for i in picked_idx] for row in sliced]
    return ParsedTable(columns=new_columns, rows=new_rows, source=table.source)


def table_to_bytes(
    table: ParsedTable,
    *,
    fmt: str = "tsv",
    include_header: bool = True,
) -> Tuple[bytes, str, str]:
    fmt_norm = (fmt or "").strip().lower()
    if fmt_norm in ("tsv", "txt", "dat", "origin"):
        delimiter = "\t"
        if fmt_norm == "tsv":
            ext = ".tsv"
            mime = "text/tab-separated-values"
        elif fmt_norm == "txt":
            ext = ".txt"
            mime = "text/plain"
        else:
            ext = ".dat"
            mime = "text/plain"
    elif fmt_norm == "csv":
        delimiter = ","
        ext = ".csv"
        mime = "text/csv"
    else:
        raise ValueError("不支持的导出格式：请选择 csv / tsv / txt / dat")

    buf = io.StringIO(newline="")
    writer = csv.writer(buf, delimiter=delimiter, lineterminator="\n")
    if include_header:
        writer.writerow(table.columns)
    writer.writerows(table.rows)
    return buf.getvalue().encode("utf-8-sig"), mime, ext


def extract_file_to_bytes(
    *,
    filename: str,
    data: bytes,
    columns_spec: str,
    start_row: int = 1,
    end_row: Optional[int] = None,
    max_rows: Optional[int] = None,
    row_keyword: Optional[str] = None,
    out_fmt: str = "tsv",
    include_header: bool = True,
) -> Tuple[bytes, str, str]:
    parsed = parse_table_from_bytes(filename, data)
    requested = split_columns_spec(columns_spec)
    extracted = extract_table(
        parsed,
        columns=requested,
        start_row=start_row,
        end_row=end_row,
        max_rows=max_rows,
        row_keyword=row_keyword,
    )
    return table_to_bytes(extracted, fmt=out_fmt, include_header=include_header)


def read_file_bytes(path: str | Path) -> Tuple[str, bytes]:
    p = Path(path)
    return p.name, p.read_bytes()
