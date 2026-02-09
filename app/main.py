from fastapi import FastAPI, File, UploadFile, HTTPException

from app.ocr_service import process_file
from app.schemas import UploadResponse

app = FastAPI(
    title="报告识别服务",
    description="上传检验/检测报告文件（PDF 或图片），自动识别出厂编码、生产厂家、设备型号、是否盖章等关键信息。",
    version="1.0.0",
)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@app.post(
    "/upload",
    response_model=UploadResponse,
    summary="上传报告文件",
    description="上传 PDF 或图片格式的报告文件，系统通过 OCR 识别并提取：出厂编码、生产厂家、设备型号、是否盖章。",
)
async def upload_report(
    file: UploadFile = File(..., description="报告文件（支持 PDF、PNG、JPG、BMP、TIFF）"),
):
    # 校验文件扩展名
    filename = file.filename or ""
    suffix = ""
    if "." in filename:
        suffix = "." + filename.rsplit(".", 1)[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {suffix}，请上传 PDF 或图片文件（{', '.join(ALLOWED_EXTENSIONS)}）",
        )

    # 读取文件内容
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过 20MB 限制")

    try:
        report = await process_file(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件处理失败: {e}")

    return UploadResponse(success=True, message="识别完成", data=report)


@app.get("/health", summary="健康检查")
async def health():
    return {"status": "ok"}
