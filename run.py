# 从 app 包中导入我们即将创建的 create_app 函数
from app import create_app
import os

# 调用工厂函数，创建 app 实例
app = create_app()

# 这部分代码只在本地直接运行 run.py 时执行
# Render/Gunicorn 会直接使用上面的 app 对象，而不会运行下面的代码
if __name__ == '__main__':
    # Render 可能会通过 PORT 环境变量指定端口
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)