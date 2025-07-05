# app/views/map_routes.py

from flask import Blueprint, request, jsonify
import pandas as pd
import uuid

# 创建一个名为 'map_bp' 的蓝图
map_bp = Blueprint('map_bp', __name__, url_prefix='/map')

# 【修改】将 PROCESSED_DATA 从单个变量变成一个字典
# 它将像这样存储数据: {'session_id_1': [points...], 'session_id_2': [points...]}
# 这就是我们的“临时内存数据库”
PROCESSED_DATA = {}


@map_bp.route('/upload', methods=['POST'])
def upload_file():
    # 【修改】从请求的表单中获取 session_id
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'message': '缺少 session_id'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '请求中未包含文件部分'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择任何文件'}), 400

    if file:
        try:
            df = pd.read_excel(file)
            df_renamed = df.rename(columns={
                '经度': 'lng', '纬度': 'lat',
                '污染物浓度': 'concentration', '标记名称': 'name'
            })

            required_columns = ['lng', 'lat', 'concentration', 'name']
            if not all(col in df_renamed.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df_renamed.columns]
                return jsonify({'success': False, 'message': f'Excel文件中缺少必要的列: {", ".join(missing)}'}), 400

            # 【修改】将数据存入以 session_id 为键的字典中
            PROCESSED_DATA[session_id] = df_renamed.to_dict('records')

            return jsonify({'success': True, 'message': f'文件 "{file.filename}" 已为会话 {session_id} 处理成功!'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'文件解析失败: {str(e)}'}), 500

    return jsonify({'success': False, 'message': '未知错误'}), 500


@map_bp.route('/get-data', methods=['GET'])
def get_data():
    # 【修改】从请求的URL参数中获取 session_id
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'message': '缺少 session_id'}), 400

    # 【修改】从字典中根据 session_id 获取对应的数据
    user_data = PROCESSED_DATA.get(session_id)

    if user_data is not None:
        data_with_id = [dict(p, id=i) for i, p in enumerate(user_data)]
        return jsonify({'success': True, 'points': data_with_id})
    else:
        # 如果这个session_id没有对应的数据，返回空列表
        return jsonify({'success': True, 'points': []})

