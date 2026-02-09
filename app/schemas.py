from pydantic import BaseModel
from typing import Optional


class ReportField(BaseModel):
    """识别报告中提取的字段"""

    factory_code: Optional[str] = None
    """出厂编码"""

    manufacturer: Optional[str] = None
    """生产厂家"""

    device_model: Optional[str] = None
    """设备型号"""

    has_stamp: bool = False
    """是否盖章"""


class UploadResponse(BaseModel):
    """上传接口返回结果"""

    success: bool
    message: str
    data: Optional[ReportField] = None
