from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_file

from table_extractor import extract_file_to_bytes


app = Flask(__name__, static_folder="static", static_url_path="/static")


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return int(value)


def _parse_bool(value: Optional[str], default: bool = True) -> bool:
    if value is None:
        return default
    value = value.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


@app.route("/", methods=["GET"])
def index():
    return app.send_static_file("index.html")


@app.route("/api/extract", methods=["POST"])
def api_extract():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "未上传文件（字段名：files）"}), 400

    columns_spec = (request.form.get("columns") or "").strip()

    out_fmt = (request.form.get("out_fmt") or "tsv").strip().lower()
    start_row = _parse_int(request.form.get("start_row")) or 1
    end_row = _parse_int(request.form.get("end_row"))
    max_rows = _parse_int(request.form.get("max_rows"))
    row_keyword = (request.form.get("row_keyword") or "").strip() or None
    include_header = _parse_bool(request.form.get("include_header"), True)
    no_header = _parse_bool(request.form.get("no_header"), False)
    if no_header:
        include_header = False

    if start_row < 1:
        return jsonify({"error": "start_row 必须 >= 1"}), 400

    outputs: list[tuple[str, bytes, str]] = []
    try:
        for f in files:
            in_name = f.filename or "uploaded"
            data = f.read()
            out_bytes, mime, ext = extract_file_to_bytes(
                filename=in_name,
                data=data,
                columns_spec=columns_spec,
                start_row=start_row,
                end_row=end_row,
                max_rows=max_rows,
                row_keyword=row_keyword,
                out_fmt=out_fmt,
                include_header=include_header,
            )
            out_name = f"{Path(in_name).stem}_extracted{ext}"
            outputs.append((out_name, out_bytes, mime))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if len(outputs) == 1:
        out_name, out_bytes, mime = outputs[0]
        return send_file(
            io.BytesIO(out_bytes),
            mimetype=mime,
            as_attachment=True,
            attachment_filename=out_name,
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for out_name, out_bytes, _mime in outputs:
            zf.writestr(out_name, out_bytes)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        attachment_filename="extracted.zip",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
