"""Build corpus v3: src/*.md (JSON meta + '\n---\n' + markdown) -> pdf/<file>.pdf"""
import json, subprocess, sys, pathlib, tempfile, html
import markdown
from stamp import stamp

ROOT = pathlib.Path(__file__).parent
CSS = """
body{font-family:'DejaVu Sans',sans-serif;font-size:10.2pt;line-height:1.45;color:#212121}
h1{font-size:17pt;color:#0d47a1;margin:0 0 4pt}
h2{font-size:12.5pt;color:#0d47a1;border-bottom:1px solid #90caf9;padding-bottom:2pt;margin-top:16pt;page-break-after:avoid}
h3{font-size:10.8pt;color:#1a237e;margin:10pt 0 3pt;page-break-after:avoid}
table{border-collapse:collapse;width:100%;margin:5pt 0 8pt;page-break-inside:auto}
tr{page-break-inside:avoid}
th,td{border:1px solid #b0bec5;padding:3pt 5pt;vertical-align:top;font-size:9.4pt}
th{background:#e3f2fd;text-align:left}
.ref{border-left:3px solid #1565c0;background:#f1f8ff;padding:4pt 7pt;margin:6pt 0;font-size:9.4pt}
.note{border-left:3px solid #ef6c00;background:#fff8e1;padding:4pt 7pt;margin:6pt 0;font-size:9.4pt}
.cover{page-break-after:always}
.company{font-size:10pt;color:#455a64;letter-spacing:1px}
.badge{display:inline-block;padding:2pt 8pt;color:#fff;font-weight:bold;font-size:9pt;border-radius:3px}
.disc{font-size:8.6pt;color:#616161;margin-top:14pt;border-top:1px solid #e0e0e0;padding-top:5pt}
ul,ol{margin:2pt 0 5pt 0;padding-left:16pt} li{margin:1pt 0}
"""
COLORS = {"PUBLIC": "#2e7d32", "INTERNAL": "#1565c0", "CONFIDENTIAL": "#e65100", "RESTRICTED": "#c62828"}

def cover(m):
    rows = [("Mã tài liệu", m["code"]), ("Tên tài liệu", m["title"]), ("Phiên bản", m["version"]),
            ("Ngày ban hành", m["issued"]), ("Ngày hiệu lực", m["effective"]),
            ("Mức phân loại", m["classification"]), ("Phạm vi người đọc", m["audience"]),
            ("Đơn vị sở hữu", m["owner"]), ("Người phê duyệt", m["approver"])]
    if m.get("supersedes"): rows.append(("Thay thế", m["supersedes"]))
    if m.get("superseded_by"): rows.append(("Được thay thế bởi", m["superseded_by"]))
    rows.append(("Chu kỳ rà soát", m["review"]))
    trs = "".join(f"<tr><th style='width:32%'>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k, v in rows)
    return (f"<div class='cover'><div class='company'>CÔNG TY CỔ PHẦN CÔNG NGHỆ NOVA DIGITAL</div>"
            f"<h1>{html.escape(m['title'])}</h1>"
            f"<span class='badge' style='background:{COLORS[m['classification']]}'>{m['classification']}</span>"
            f"<h3>Kiểm soát tài liệu</h3><table>{trs}</table>"
            "<div class='disc'>Tài liệu mô phỏng của một công ty giả định, dùng để kiểm thử hệ thống Enterprise AI "
            "Knowledge Assistant. Không sử dụng làm tư vấn pháp lý hoặc căn cứ xử lý người lao động thực tế. "
            "Khi nội dung khác với quy định pháp luật bắt buộc hoặc thỏa thuận hợp pháp có lợi hơn cho người lao động, "
            "áp dụng quy định pháp luật hoặc thỏa thuận đó.</div></div>")

def build(md_path):
    raw = md_path.read_text(encoding="utf-8")
    meta_s, body = raw.split("\n---\n", 1)
    m = json.loads(meta_s)
    body_html = markdown.markdown(body, extensions=["tables", "md_in_html", "attr_list", "sane_lists"])
    doc = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{cover(m)}{body_html}</body></html>"
    with tempfile.TemporaryDirectory() as td:
        h = pathlib.Path(td, "d.html"); h.write_text(doc, encoding="utf-8")
        raw_pdf = pathlib.Path(td, "raw.pdf")
        subprocess.run(["wkhtmltopdf", "-q", "--encoding", "utf-8", "-s", "A4", "-T", "20mm", "-B", "18mm",
                        "-L", "15mm", "-R", "15mm", "--enable-local-file-access", str(h), str(raw_pdf)], check=True)
        out = ROOT / "pdf" / (m["file"] + ".pdf")
        stamp(str(raw_pdf), str(out), m["code"], m["version"], m["classification"])
    return out

if __name__ == "__main__":
    targets = sys.argv[1:] or sorted(str(p) for p in (ROOT / "src").glob("*.md"))
    for t in targets: print(build(pathlib.Path(t)))
