"""Sinh bộ 10 tài liệu sản phẩm thực phẩm đóng gói đa định dạng (5 DOCX + 5 PDF) cho thí nghiệm P05-E01.

Cảnh báo dữ liệu: Toàn bộ 10 tài liệu này là dữ liệu tổng hợp (`synthetic`) phục vụ đo độ chính xác
trích xuất của Docling trên tiếng Việt có dấu, bảng biểu và nhiều kiểu ghi giá/khối lượng/hạn dùng.
Tuyệt đối không dùng làm hồ sơ OCOP thật.
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from fpdf import FPDF

E01_DIR = Path(__file__).resolve().parent
DOCS_DIR = E01_DIR / "sample_docs"

# Đường dẫn font Unicode hệ thống Windows hỗ trợ đầy đủ dấu tiếng Việt trong PDF
WINDOWS_FONT_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
WINDOWS_FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")


# Đặc tả 10 tài liệu mẫu cùng đáp án chuẩn (ground truth) cho 4 trường cứng
SAMPLE_SPECS = [
    {
        "doc_id": "doc01_honey_table.docx",
        "format": "docx",
        "layout": "table_standard",
        "sku_id": "SKU-HONEY-01",
        "title": "PHIẾU THÔNG TIN SẢN PHẨM — MẬT ONG HOA CÀ PHÊ ĐẮK LẮK",
        "price_text": "159.000 đ",
        "weight_text": "500ml",
        "expiry_text": "24 tháng",
        "origin_text": "Đắk Lắk",
        "extra_note": "Thành phần: 100% mật ong hoa cà phê tự nhiên. Bảo quản nơi khô ráo, tránh nắng trực tiếp.",
        "gold": {
            "price_vnd": 159000,
            "weight": "500ml",
            "expiry": "24 tháng",
            "origin": "Đắk Lắk",
        },
    },
    {
        "doc_id": "doc02_tea_prose.docx",
        "format": "docx",
        "layout": "prose_only",
        "sku_id": "SKU-TEA-02",
        "title": "MÔ TẢ SẢN PHẨM TRÀ SHAN TUYẾT CỔ THỤ HÀ GIANG",
        "price_text": "245.000 VNĐ",
        "weight_text": "100g",
        "expiry_text": "18 tháng",
        "origin_text": "Hà Giang",
        "extra_note": "Sản phẩm thu hái thủ công từ cây trà cổ thụ trên độ cao 1.300m, hương cốm nhẹ và hậu ngọt sâu.",
        "gold": {
            "price_vnd": 245000,
            "weight": "100g",
            "expiry": "18 tháng",
            "origin": "Hà Giang",
        },
    },
    {
        "doc_id": "doc03_cashew_mixed.docx",
        "format": "docx",
        "layout": "mixed_table_faq",
        "sku_id": "SKU-CASHEW-03",
        "title": "HỒ SƠ SẢN PHẨM HẠT ĐIỀU RANG CỦI VỎ LỤA",
        "price_text": "185k",
        "weight_text": "500g",
        "expiry_text": "12 tháng",
        "origin_text": "Bình Phước",
        "extra_note": "Lưu ý dị ứng: sản phẩm chứa hạt cây, không phù hợp với người dị ứng các loại hạt.",
        "gold": {
            "price_vnd": 185000,
            "weight": "500g",
            "expiry": "12 tháng",
            "origin": "Bình Phước",
        },
    },
    {
        "doc_id": "doc04_mango_table.docx",
        "format": "docx",
        "layout": "table_comma_price",
        "sku_id": "SKU-MANGO-04",
        "title": "BẢNG THÔNG SỐ XOÀI SẤY DẺO CAM LÂM",
        "price_text": "129,000 đồng",
        "weight_text": "0.5 kg",
        "expiry_text": "12 tháng",
        "origin_text": "Khánh Hòa",
        "extra_note": "Không phẩm màu nhân tạo, đóng túi zip bạc giữ độ mềm dẻo tự nhiên.",
        "gold": {
            "price_vnd": 129000,
            "weight": "0.5 kg",
            "expiry": "12 tháng",
            "origin": "Khánh Hòa",
        },
    },
    {
        "doc_id": "doc05_coffee_informal.docx",
        "format": "docx",
        "layout": "bullet_notes",
        "sku_id": "SKU-COFFEE-05",
        "title": "GHI CHÚ BÁN HÀNG — CÀ PHÊ RANG XAY BUÔN MA THUỘT",
        "price_text": "210.000đ",
        "weight_text": "250g",
        "expiry_text": "12 tháng",
        "origin_text": "Đắk Lắk",
        "extra_note": "Rang mộc nguyên chất, phù hợp pha phin truyền thống hoặc pha máy.",
        "gold": {
            "price_vnd": 210000,
            "weight": "250g",
            "expiry": "12 tháng",
            "origin": "Đắk Lắk",
        },
    },
    {
        "doc_id": "doc06_honey_spec.pdf",
        "format": "pdf",
        "layout": "pdf_table",
        "sku_id": "SKU-HONEY-01",
        "title": "THÔNG SỐ KỸ THUẬT — MẬT ONG HOA CÀ PHÊ",
        "price_text": "159.000đ",
        "weight_text": "500ml",
        "expiry_text": "24 tháng",
        "origin_text": "Đắk Lắk",
        "extra_note": "Không dùng cho trẻ em dưới 1 tuổi. Hiện tượng kết tinh tự nhiên ở nhiệt độ thấp là bình thường.",
        "gold": {
            "price_vnd": 159000,
            "weight": "500ml",
            "expiry": "24 tháng",
            "origin": "Đắk Lắk",
        },
    },
    {
        "doc_id": "doc07_tea_catalog.pdf",
        "format": "pdf",
        "layout": "pdf_prose",
        "sku_id": "SKU-TEA-02",
        "title": "CATALOG SẢN PHẨM — TRÀ SHAN TUYẾT CỔ THỤ",
        "price_text": "245,000 VNĐ",
        "weight_text": "100g",
        "expiry_text": "18 tháng",
        "origin_text": "Hà Giang",
        "extra_note": "Hãm nước 85-90 độ C trong 30-45 giây, pha được từ 6 đến 8 lần nước.",
        "gold": {
            "price_vnd": 245000,
            "weight": "100g",
            "expiry": "18 tháng",
            "origin": "Hà Giang",
        },
    },
    {
        "doc_id": "doc08_cashew_label.pdf",
        "format": "pdf",
        "layout": "pdf_label",
        "sku_id": "SKU-CASHEW-03",
        "title": "NHÃN BAO BÌ THỰC PHẨM — HẠT ĐIỀU RANG CỦI",
        "price_text": "185.000 đồng",
        "weight_text": "500g",
        "expiry_text": "12 tháng",
        "origin_text": "Bình Phước",
        "extra_note": "Thành phần: 99% hạt điều nhân sống Bình Phước, 1% muối tinh. Đóng nắp kín sau khi dùng.",
        "gold": {
            "price_vnd": 185000,
            "weight": "500g",
            "expiry": "12 tháng",
            "origin": "Bình Phước",
        },
    },
    {
        "doc_id": "doc09_ginger_tea.pdf",
        "format": "pdf",
        "layout": "pdf_table",
        "sku_id": "SKU-GINGER-06",
        "title": "PHIẾU THÔNG TIN — TRÀ GỪNG MẬT ONG ĐÀ LẠT",
        "price_text": "95k",
        "weight_text": "200g",
        "expiry_text": "18 tháng",
        "origin_text": "Lâm Đồng",
        "extra_note": "Pha 1 gói nhỏ với 120ml nước nóng, uống ấm vào buổi sáng hoặc khi thời tiết lạnh.",
        "gold": {
            "price_vnd": 95000,
            "weight": "200g",
            "expiry": "18 tháng",
            "origin": "Lâm Đồng",
        },
    },
    {
        "doc_id": "doc10_macadamia_sheet.pdf",
        "format": "pdf",
        "layout": "pdf_table",
        "sku_id": "SKU-MACA-07",
        "title": "BẢN CÔNG BỐ THÔNG TIN — HẠT MẮC CA SẤY NỨT VỎ",
        "price_text": "320.000đ",
        "weight_text": "500 gram",
        "expiry_text": "12 tháng",
        "origin_text": "Lâm Đồng",
        "extra_note": "Kèm dụng cụ tách vỏ inox trong mỗi hộp. Bảo quản nơi thoáng mát, tránh ẩm mốc.",
        "gold": {
            "price_vnd": 320000,
            "weight": "500 gram",
            "expiry": "12 tháng",
            "origin": "Lâm Đồng",
        },
    },
]


def create_docx(spec: dict, out_path: Path) -> None:
    """Tạo file DOCX theo bố cục chỉ định (bảng, văn xuôi, hỗn hợp hoặc gạch đầu dòng)."""
    doc = Document()
    doc.add_heading(spec["title"], level=1)
    doc.add_paragraph(
        "[TÀI LIỆU MÔ PHỎNG TỔNG HỢP PHỤC VỤ THÍ NGHIỆM P05-E01 — KHÔNG PHẢI HỒ SƠ THẬT]"
    )

    layout = spec["layout"]
    if layout in ("table_standard", "table_comma_price", "mixed_table_faq"):
        table = doc.add_table(rows=5, cols=2)
        table.style = "Table Grid"
        rows_data = [
            ("Mã SKU", spec["sku_id"]),
            ("Giá bán niêm yết", spec["price_text"]),
            ("Khối lượng / Dung tích", spec["weight_text"]),
            ("Hạn sử dụng", f"{spec['expiry_text']} kể từ ngày sản xuất"),
            ("Xuất xứ", spec["origin_text"]),
        ]
        for idx, (label, val) in enumerate(rows_data):
            table.cell(idx, 0).text = label
            table.cell(idx, 1).text = val
        doc.add_paragraph("")
        doc.add_paragraph(f"Ghi chú thêm: {spec['extra_note']}")

    elif layout == "prose_only":
        doc.add_paragraph(
            f"Sản phẩm mang mã {spec['sku_id']} có xuất xứ: {spec['origin_text']}. "
            f"Quy cách đóng gói với khối lượng: {spec['weight_text']}. "
            f"Mức giá bán: {spec['price_text']}. "
            f"Hạn sử dụng: {spec['expiry_text']} kể từ ngày đóng gói."
        )
        doc.add_paragraph(spec["extra_note"])

    elif layout == "bullet_notes":
        for line in [
            f"Mã sản phẩm: {spec['sku_id']}",
            f"Giá bán: {spec['price_text']}",
            f"Khối lượng tịnh: {spec['weight_text']}",
            f"Hạn sử dụng: {spec['expiry_text']}",
            f"Xuất xứ: {spec['origin_text']}",
        ]:
            doc.add_paragraph(line, style="List Bullet")
        doc.add_paragraph(spec["extra_note"])

    doc.save(str(out_path))


def create_pdf(spec: dict, out_path: Path) -> None:
    """Tạo file PDF tiếng Việt có dấu chuẩn bằng font Unicode hệ thống (Arial TTF)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_font("ViArial", "", str(WINDOWS_FONT_REGULAR))
    pdf.add_font("ViArial", "B", str(WINDOWS_FONT_BOLD))

    pdf.set_font("ViArial", "B", 14)
    pdf.multi_cell(pdf.epw, 9, spec["title"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("ViArial", "", 9)
    pdf.multi_cell(
        pdf.epw,
        6,
        "[TÀI LIỆU MÔ PHỎNG TỔNG HỢP PHỤC VỤ THÍ NGHIỆM P05-E01 — KHÔNG PHẢI HỒ SƠ THẬT]",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    layout = spec["layout"]
    if layout == "pdf_table":
        rows = [
            ("Mã SKU", spec["sku_id"]),
            ("Giá bán", spec["price_text"]),
            ("Khối lượng", spec["weight_text"]),
            ("Hạn sử dụng", f"{spec['expiry_text']} kể từ ngày sản xuất"),
            ("Xuất xứ", spec["origin_text"]),
        ]
        for label, val in rows:
            pdf.set_font("ViArial", "B", 11)
            pdf.cell(65, 10, label, border=1)
            pdf.set_font("ViArial", "", 11)
            pdf.cell(125, 10, val, border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        pdf.set_font("ViArial", "", 11)
        pdf.multi_cell(pdf.epw, 7, f"Ghi chú: {spec['extra_note']}", new_x="LMARGIN", new_y="NEXT")

    elif layout == "pdf_prose":
        pdf.set_font("ViArial", "", 11)
        body = (
            f"Mã sản phẩm: {spec['sku_id']}\n"
            f"Giá bán chính thức: {spec['price_text']}\n"
            f"Khối lượng: {spec['weight_text']}\n"
            f"Hạn sử dụng: {spec['expiry_text']} kể từ ngày đóng gói\n"
            f"Xuất xứ: {spec['origin_text']}\n\n"
            f"Thông tin sử dụng: {spec['extra_note']}"
        )
        pdf.multi_cell(pdf.epw, 8, body, new_x="LMARGIN", new_y="NEXT")

    elif layout == "pdf_label":
        pdf.set_font("ViArial", "B", 12)
        pdf.cell(0, 8, "THÔNG TIN NHÃN SẢN PHẨM", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("ViArial", "", 11)
        for line in [
            f"- Mã SKU: {spec['sku_id']}",
            f"- Khối lượng tịnh: {spec['weight_text']}",
            f"- Giá bán lẻ đề xuất: {spec['price_text']}",
            f"- Hạn sử dụng: {spec['expiry_text']}",
            f"- Xuất xứ: {spec['origin_text']}",
            f"- Chi tiết: {spec['extra_note']}",
        ]:
            pdf.multi_cell(pdf.epw, 8, line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(out_path))


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ground_truth = {
        "dataset_meta": {
            "dataset_id": "p05-e01-synthetic-docs-v0.1",
            "data_origin": "synthetic_for_poc_validation",
            "is_synthetic": True,
            "total_documents": len(SAMPLE_SPECS),
            "note": "10 tài liệu sản phẩm thực phẩm đóng gói (5 DOCX + 5 PDF) gắn nhãn synthetic phục vụ đo độ chính xác extraction của Docling trong P05-E01.",
        },
        "documents": [],
    }

    for spec in SAMPLE_SPECS:
        out_path = DOCS_DIR / spec["doc_id"]
        if spec["format"] == "docx":
            create_docx(spec, out_path)
        else:
            create_pdf(spec, out_path)

        ground_truth["documents"].append(
            {
                "doc_id": spec["doc_id"],
                "format": spec["format"],
                "layout": spec["layout"],
                "sku_id": spec["sku_id"],
                "gold": spec["gold"],
            }
        )
        print(f"Đã tạo: {out_path.name} ({spec['format']}, layout={spec['layout']})")

    gt_path = E01_DIR / "ground_truth.json"
    gt_path.write_text(json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nHoàn tất sinh {len(SAMPLE_SPECS)} tài liệu mẫu và đáp án chuẩn tại: {gt_path}")


if __name__ == "__main__":
    main()
