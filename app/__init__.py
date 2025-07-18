# app/__init__.py

from flask import Flask
from flask_cors import CORS


def create_app():
    """
    应用工厂函数
    """
    app = Flask(__name__)

    # 允许所有来源的跨域请求
    CORS(app)

    # 初始化数据库
    from .database import init_db
    init_db()

    # 在函数内部导入并注册蓝图
    from .views.map_routes import map_bp
    from .views.heatmap_routes import heatmap_bp
    from .views.weather_routes import weather_bp
    from .views.feedback_routes import feedback_bp
    from .views.message_routes import message_bp
    from .views.admin_auth import admin_bp
    app.register_blueprint(map_bp)
    app.register_blueprint(heatmap_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(message_bp)
    app.register_blueprint(admin_bp)

    # 提供一个根路由用于健康检查
    @app.route("/")
    def index():
        return "后端服务健康运行中！"

    return app
