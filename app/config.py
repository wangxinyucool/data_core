import os
from dotenv import load_dotenv

# 找到项目根目录下的 .env 文件并加载
# os.path.dirname(__file__) 指的是当前文件(config.py)所在的目录(app)
# os.path.join(..., '..') 则是指上一级目录，也就是项目根目录
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings:
    API_KEY: str = os.getenv("OPENWEATHER_API_KEY")

settings = Settings()