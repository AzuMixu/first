import io
import re
import tempfile
from pathlib import Path
from typing import List, Optional

from PIL import Image

from app.schemas import ReportField

# PaddleOCR 延迟加载，避免启动时间过长
_ocr_instance = None


def get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR

        _ocr_instance = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    return _ocr_instance


def pdf_to_images(pdf_bytes: bytes) -> List[Image.Image]:
    """将 PDF 文件转为图片列表"""
    from pdf2image import convert_from_bytes

    return convert_from_bytes(pdf_bytes)


def ocr_from_image(image: Image.Image) -> List[str]:
    """对单张图片执行 OCR，返回识别到的所有文本行"""
    ocr = get_ocr()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
        image.save(tmp.name)
        result = ocr.ocr(tmp.name, cls=True)
    lines: List[str] = []
    if result:
        for page in result:
            if page:
                for line in page:
                    text = line[1][0] if line[1] else ""
                    if text:
                        lines.append(text)
    return lines


def extract_fields(lines: List[str]) -> ReportField:
    """从 OCR 文本行中提取目标字段"""
    full_text = "\n".join(lines)

    factory_code = _match_field(
        lines,
        [r"出厂编[码号][\s:：]*(.+)", r"出厂号[\s:：]*(.+)", r"编[码号][\s:：]*(\S+)"],
    )
    manufacturer = _match_field(
        lines,
        [r"生产厂[家商][\s:：]*(.+)", r"制造厂[家商][\s:：]*(.+)", r"厂家[\s:：]*(.+)"],
    )
    device_model = _match_field(
        lines,
        [r"设备型号[\s:：]*(.+)", r"型号[\s:：]*(.+)", r"规格型号[\s:：]*(.+)"],
    )
    has_stamp = _detect_stamp(lines, full_text)

    return ReportField(
        factory_code=_clean(factory_code),
        manufacturer=_clean(manufacturer),
        device_model=_clean(device_model),
        has_stamp=has_stamp,
    )


def _match_field(lines: List[str], patterns: List[str]) -> Optional[str]:
    """按优先级依次尝试匹配，返回第一个命中的捕获组"""
    for pattern in patterns:
        for line in lines:
            m = re.search(pattern, line)
            if m:
                return m.group(1)
    return None


def _detect_stamp(lines: List[str], full_text: str) -> bool:
    """检测是否盖章：通过关键词判断"""
    stamp_keywords = ["盖章", "公章", "印章", "专用章", "检验章", "合格章"]
    for kw in stamp_keywords:
        if kw in full_text:
            return True
    # 检测常见的章形文本特征（圆形章中的文字常被 OCR 识别为弧形排列）
    for line in lines:
        if re.search(r"有限公司$", line) and any(
            "检" in l or "验" in l or "合格" in l for l in lines
        ):
            return True
    return False


def _clean(value: Optional[str]) -> Optional[str]:
    """清理提取到的文本"""
    if value is None:
        return None
    value = value.strip().strip(":：").strip()
    return value if value else None


async def process_file(file_bytes: bytes, filename: str) -> ReportField:
    """处理上传的文件，返回提取的字段信息"""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        images = pdf_to_images(file_bytes)
    elif suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"):
        images = [Image.open(io.BytesIO(file_bytes))]
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，请上传 PDF 或图片文件")

    all_lines: List[str] = []
    for img in images:
        all_lines.extend(ocr_from_image(img))

    return extract_fields(all_lines)
