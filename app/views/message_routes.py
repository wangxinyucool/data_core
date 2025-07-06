from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from ..database import engine
from ..models import Message
import json

message_bp = Blueprint('message', __name__)
Session = sessionmaker(bind=engine)

@message_bp.route('/api/messages', methods=['POST'])
def submit_message():
    """提交留言"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['name', 'email', 'subject', 'content']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'缺少必填字段: {field}'}), 400
        
        # 获取设备信息
        device_info = data.get('device_info', '')
        
        session = Session()
        
        # 创建新留言
        new_message = Message(
            name=data['name'],
            email=data['email'],
            subject=data['subject'],
            content=data['content'],
            device_info=device_info
        )
        
        session.add(new_message)
        session.commit()
        
        session.close()
        
        return jsonify({
            'success': True,
            'message': '留言提交成功',
            'id': new_message.id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'提交失败: {str(e)}'}), 500

@message_bp.route('/api/messages', methods=['GET'])
def get_messages():
    """获取留言列表（管理员用）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        status = request.args.get('status', '')  # all, unread, read
        
        session = Session()
        
        # 构建查询
        query = session.query(Message)
        
        # 搜索过滤
        if search:
            query = query.filter(
                (Message.name.contains(search)) |
                (Message.email.contains(search)) |
                (Message.subject.contains(search)) |
                (Message.content.contains(search))
            )
        
        # 状态过滤
        if status == 'unread':
            query = query.filter(Message.is_read == False)
        elif status == 'read':
            query = query.filter(Message.is_read == True)
        
        # 按时间倒序排列
        query = query.order_by(desc(Message.created_at))
        
        # 分页
        total = query.count()
        messages = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # 转换为字典
        message_list = []
        for msg in messages:
            message_list.append({
                'id': msg.id,
                'name': msg.name,
                'email': msg.email,
                'subject': msg.subject,
                'content': msg.content,
                'device_info': msg.device_info,
                'created_at': msg.created_at.isoformat() if msg.created_at else None,
                'is_read': msg.is_read,
                'is_replied': msg.is_replied
            })
        
        session.close()
        
        return jsonify({
            'success': True,
            'data': message_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}'}), 500

@message_bp.route('/api/messages/<int:message_id>', methods=['GET'])
def get_message_detail(message_id):
    """获取留言详情"""
    try:
        session = Session()
        message = session.query(Message).filter(Message.id == message_id).first()
        
        if not message:
            session.close()
            return jsonify({'error': '留言不存在'}), 404
        
        # 标记为已读
        message.is_read = True
        session.commit()
        
        message_data = {
            'id': message.id,
            'name': message.name,
            'email': message.email,
            'subject': message.subject,
            'content': message.content,
            'device_info': message.device_info,
            'created_at': message.created_at.isoformat() if message.created_at else None,
            'is_read': message.is_read,
            'is_replied': message.is_replied
        }
        
        session.close()
        
        return jsonify({
            'success': True,
            'data': message_data
        })
        
    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}'}), 500

@message_bp.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    """删除留言"""
    try:
        session = Session()
        message = session.query(Message).filter(Message.id == message_id).first()
        
        if not message:
            session.close()
            return jsonify({'error': '留言不存在'}), 404
        
        session.delete(message)
        session.commit()
        session.close()
        
        return jsonify({
            'success': True,
            'message': '留言删除成功'
        })
        
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

@message_bp.route('/api/messages/batch-delete', methods=['POST'])
def batch_delete_messages():
    """批量删除留言"""
    try:
        data = request.get_json()
        message_ids = data.get('ids', [])
        
        if not message_ids:
            return jsonify({'error': '请选择要删除的留言'}), 400
        
        session = Session()
        
        # 删除选中的留言
        deleted_count = session.query(Message).filter(Message.id.in_(message_ids)).delete(synchronize_session=False)
        session.commit()
        session.close()
        
        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 条留言'
        })
        
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

@message_bp.route('/api/messages/<int:message_id>/reply', methods=['POST'])
def mark_as_replied(message_id):
    """标记留言为已回复"""
    try:
        session = Session()
        message = session.query(Message).filter(Message.id == message_id).first()
        
        if not message:
            session.close()
            return jsonify({'error': '留言不存在'}), 404
        
        message.is_replied = True
        session.commit()
        session.close()
        
        return jsonify({
            'success': True,
            'message': '已标记为已回复'
        })
        
    except Exception as e:
        return jsonify({'error': f'操作失败: {str(e)}'}), 500

@message_bp.route('/api/messages/stats', methods=['GET'])
def get_message_stats():
    """获取留言统计信息"""
    try:
        session = Session()
        
        total = session.query(Message).count()
        unread = session.query(Message).filter(Message.is_read == False).count()
        replied = session.query(Message).filter(Message.is_replied == True).count()
        
        session.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'unread': unread,
                'replied': replied,
                'unreplied': total - replied
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'获取统计失败: {str(e)}'}), 500 