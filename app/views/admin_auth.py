import os
import hashlib
from flask import Blueprint, request, jsonify

admin_bp = Blueprint('admin_auth', __name__)

ADMIN_FILE = os.path.join(os.path.dirname(__file__), '../../admin_account.txt')

# 读取所有管理员账户（每两行为一组：用户名+哈希密码）
def get_all_admin_accounts():
    if not os.path.exists(ADMIN_FILE):
        return []
    with open(ADMIN_FILE, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
        accounts = []
        for i in range(0, len(lines)-1, 2):
            accounts.append((lines[i], lines[i+1]))
        return accounts

@admin_bp.route('/api/admin-login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    accounts = get_all_admin_accounts()
    for user, pwd_hash in accounts:
        if username == user and hashlib.sha256(password.encode()).hexdigest() == pwd_hash:
            return jsonify({'success': True})
    return jsonify({'success': False, 'msg': '账号或密码错误'}), 401 