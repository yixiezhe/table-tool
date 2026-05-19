from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from table_extractor import extract_file_to_bytes, read_file_bytes


def _prompt_int(label: str, default: int | None) -> int | None:
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"{label}{suffix}: ").strip()
    if not raw:
        return default
    return int(raw)


def _prompt_str(label: str, default: str | None) -> str:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{label}{suffix}: ").strip()
    return raw or (default or "")


def _prompt_bool(label: str, default: bool) -> bool:
    suffix = " [Y]" if default else " [N]"
    raw = input(f"{label}{suffix}: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true", "t", "是", "要"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="从表格类文件中按列/行抽取并导出（支持 .DTA / .mdat / .z/.cor / CSV / TSV / TXT 等）"
    )
    p.add_argument("files", nargs="+", help="输入文件路径（可多个）")
    p.add_argument("-c", "--columns", help="要提取的列名（逗号/空格分隔，如: Zreal,Zimag；留空则导出全部列）")
    p.add_argument("--start-row", type=int, default=1, help="数据起始行（从 1 开始，不含表头）")
    p.add_argument("--end-row", type=int, default=None, help="数据结束行（包含该行）")
    p.add_argument("--max-rows", type=int, default=None, help="最多提取多少行（从 start-row 开始计）")
    p.add_argument("--row-keyword", default=None, help="仅保留包含该关键词的行（任意单元格命中）")
    p.add_argument(
        "-f",
        "--out-fmt",
        default="tsv",
        choices=["csv", "tsv", "txt", "dat"],
        help="导出格式（Origin 推荐 txt/dat 或 tsv）",
    )
    p.add_argument("-o", "--out-dir", default="out", help="输出目录（默认 out）")
    p.add_argument("--no-header", action="store_true", help="导出时不包含表头（列名行）")
    p.add_argument("--notepad", action="store_true", help="先用记事本打开输入文件")
    p.add_argument("--interactive", action="store_true", help="无参数时走交互式提问")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    columns_spec = args.columns or ""
    if args.interactive:
        if args.notepad:
            for f in args.files:
                subprocess.Popen(["notepad.exe", str(Path(f).resolve())])

        columns_spec = _prompt_str("请输入要提取的列名（逗号/空格分隔，留空导出全部列）", columns_spec or None)
        out_fmt = _prompt_str("请选择导出格式 csv/tsv/txt/dat", args.out_fmt)
        start_row = _prompt_int("起始数据行 start_row", args.start_row)
        max_rows = _prompt_int("最多提取行数 max_rows（空表示不限）", args.max_rows)
        end_row = _prompt_int("结束数据行 end_row（空表示不限）", args.end_row)
        row_keyword = _prompt_str("行关键词 row_keyword（空表示不过滤）", args.row_keyword)
        include_header = _prompt_bool("导出是否包含表头（列名行）", not args.no_header)
        args.out_fmt = out_fmt.strip() or args.out_fmt
        args.start_row = start_row or 1
        args.max_rows = max_rows
        args.end_row = end_row
        args.row_keyword = row_keyword.strip() or None
        args.no_header = not include_header

    for f in args.files:
        in_path = Path(f)
        filename, data = read_file_bytes(in_path)
        try:
            out_bytes, _mime, ext = extract_file_to_bytes(
                filename=filename,
                data=data,
                columns_spec=columns_spec,
                start_row=args.start_row,
                end_row=args.end_row,
                max_rows=args.max_rows,
                row_keyword=args.row_keyword,
                out_fmt=args.out_fmt,
                include_header=not args.no_header,
            )
        except Exception as e:
            print(f"处理失败: {in_path} -> {e}", file=sys.stderr)
            return 1

        out_name = f"{in_path.stem}_extracted{ext}"
        out_path = out_dir / out_name
        out_path.write_bytes(out_bytes)
        print(f"OK: {in_path.name} -> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
