# 文件路径: app/views/heatmap_routes.py

from flask import Blueprint, request, jsonify
import json
from app.services.heatmap_service import create_heatmap_image

# 1. 创建一个专门用于热力图功能的新蓝图(Blueprint)
# 我们为它指定一个URL前缀'/api/heatmap'，这样所有属于这个蓝图的路由都会在这个路径下
heatmap_bp = Blueprint('heatmap', __name__, url_prefix='/api/heatmap')


# 2. 在新的蓝图上定义我们的路由
# 因为有了URL前缀，这里的路径可以是更简洁的'/generate'
# 最终的完整API地址是: /api/heatmap/generate
@heatmap_bp.route('/generate', methods=['POST'])
def generate_heatmap():
    """
    接收前端请求，生成热力图的API端点。
    """
    if 'excelFile' not in request.files:
        return jsonify({"status": "error", "message": "请求中缺少 'excelFile' 文件部分"}), 400

    file = request.files['excelFile']
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择任何文件"}), 400

    if file:
        try:
            options_str = request.form.get('options', '{}')
            options = json.loads(options_str)

            base64_image = create_heatmap_image(file, options)

            if base64_image:
                return jsonify({
                    "status": "success",
                    "message": "热力图生成成功",
                    "image_base64": base64_image
                })
            else:
                return jsonify({"status": "error", "message": "后端生成热力图失败，请检查服务器日志"}), 500

        except json.JSONDecodeError:
            return jsonify({"status": "error", "message": "选项(options)字段的JSON格式错误"}), 400
        except Exception as e:
            print(f"Unhandled error: {e}")
            return jsonify({"status": "error", "message": "服务器内部错误"}), 500

    return jsonify({"status": "error", "message": "无效的文件或请求"}), 400