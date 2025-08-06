from flask import Blueprint, jsonify
from ..database import get_db
from ..models import Feedback, Message

health_bp = Blueprint('health', __name__, url_prefix='/api')

@health_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        # 测试数据库连接
        db = next(get_db())
        
        # 检查表是否存在
        feedback_count = db.query(Feedback).count()
        message_count = db.query(Message).count()
        
        db.close()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'tables': {
                'feedback': {
                    'exists': True,
                    'record_count': feedback_count
                },
                'messages': {
                    'exists': True,
                    'record_count': message_count
                }
            },
            'timestamp': '2025-01-27T12:00:00Z'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': '2025-01-27T12:00:00Z'
        }), 500

@health_bp.route('/ping', methods=['GET'])
def ping():
    """简单的ping端点"""
    return jsonify({
        'message': 'pong',
        'status': 'ok'
    }), 200 