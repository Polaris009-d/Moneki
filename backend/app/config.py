"""应用配置：路径与 DeepSeek 环境变量。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = BASE_DIR.parent / "data"                # 项目根/data/

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # 未安装 dotenv 时静默跳过，环境变量仍可用
    pass


class Settings:
    # 数据与数据库路径
    data_dir: Path = DATA_DIR
    db_path: Path = DATA_DIR / "moneki.db"

    # DeepSeek（OpenAI 兼容接口）
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")


settings = Settings()
