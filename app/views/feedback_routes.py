from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Feedback

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')

@feedback_bp.route('/', methods=['GET'])
def get_all_feedback():
    """获取所有反馈（简单版本）"""
    try:
        db = next(get_db())
        feedback_list = db.query(Feedback).order_by(Feedback.timestamp.desc()).all()
        
        return jsonify({
            'success': True,
            'data': {
                'feedback_list': [f.to_dict() for f in feedback_list],
                'total': len(feedback_list)
            }
        })
        
    except Exception as e:
        print(f"获取反馈列表时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500

@feedback_bp.route('/submit', methods=['POST'])
def submit_feedback():
    """提交用户反馈"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        if not data or 'rating' not in data or 'suggestion' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必要字段：rating 和 suggestion'
            }), 400
        
        rating = data.get('rating')
        suggestion = data.get('suggestion')
        
        # 验证评分范围
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({
                'success': False,
                'message': '评分必须在1-5之间'
            }), 400
        
        # 验证建议内容
        if not suggestion or not suggestion.strip():
            return jsonify({
                'success': False,
                'message': '建议内容不能为空'
            }), 400
        
        # 获取请求信息
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        device_info = data.get('deviceInfo', {})
        
        # 创建反馈记录
        feedback = Feedback(
            rating=rating,
            suggestion=suggestion.strip(),
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 保存到数据库
        db = next(get_db())
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        return jsonify({
            'success': True,
            'message': '反馈提交成功',
            'data': {
                'id': feedback.id,
                'rating': feedback.rating,
                'timestamp': feedback.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        print(f"提交反馈时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500

@feedback_bp.route('/stats', methods=['GET'])
def get_feedback_stats():
    """获取反馈统计信息（管理员用）"""
    try:
        db = next(get_db())
        
        # 获取总反馈数
        total_feedback = db.query(Feedback).count()
        
        # 获取平均评分
        avg_rating = db.query(Feedback.rating).all()
        if avg_rating:
            avg_rating = sum([r[0] for r in avg_rating]) / len(avg_rating)
        else:
            avg_rating = 0
        
        # 获取评分分布
        rating_distribution = {}
        for i in range(1, 6):
            count = db.query(Feedback).filter(Feedback.rating == i).count()
            rating_distribution[f"{i}星"] = count
        
        # 获取最近的反馈
        recent_feedback = db.query(Feedback).order_by(Feedback.timestamp.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'data': {
                'total_feedback': total_feedback,
                'average_rating': round(avg_rating, 2),
                'rating_distribution': rating_distribution,
                'recent_feedback': [f.to_dict() for f in recent_feedback]
            }
        })
        
    except Exception as e:
        print(f"获取反馈统计时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500

@feedback_bp.route('/list', methods=['GET'])
def get_feedback_list():
    """获取反馈列表（管理员用）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        db = next(get_db())
        
        # 分页查询
        offset = (page - 1) * per_page
        feedback_list = db.query(Feedback).order_by(Feedback.timestamp.desc()).offset(offset).limit(per_page).all()
        
        # 获取总数
        total = db.query(Feedback).count()
        
        return jsonify({
            'success': True,
            'data': {
                'feedback_list': [f.to_dict() for f in feedback_list],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        })
        
    except Exception as e:
        print(f"获取反馈列表时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500

@feedback_bp.route('/delete/<int:feedback_id>', methods=['DELETE'])
def delete_feedback(feedback_id):
    """删除指定反馈（管理员用）"""
    try:
        db = next(get_db())
        
        # 查找要删除的反馈
        feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
        
        if not feedback:
            return jsonify({
                'success': False,
                'message': '反馈不存在'
            }), 404
        
        # 删除反馈
        db.delete(feedback)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': '反馈删除成功',
            'data': {
                'deleted_id': feedback_id
            }
        })
        
    except Exception as e:
        print(f"删除反馈时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500

@feedback_bp.route('/batch-delete', methods=['POST'])
def batch_delete_feedback():
    """批量删除反馈（管理员用）"""
    try:
        data = request.get_json()
        feedback_ids = data.get('feedback_ids', [])
        
        if not feedback_ids:
            return jsonify({
                'success': False,
                'message': '请选择要删除的反馈'
            }), 400
        
        db = next(get_db())
        
        # 查找并删除指定的反馈
        deleted_count = 0
        for feedback_id in feedback_ids:
            feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
            if feedback:
                db.delete(feedback)
                deleted_count += 1
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 条反馈',
            'data': {
                'deleted_count': deleted_count,
                'deleted_ids': feedback_ids
            }
        })
        
    except Exception as e:
        print(f"批量删除反馈时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500 