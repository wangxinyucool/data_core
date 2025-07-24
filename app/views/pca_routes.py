import os
import pandas as pd
import numpy as np
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
import json
import tempfile
import zipfile
from datetime import datetime
import uuid

pca_bp = Blueprint('pca', __name__)

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'pca')
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# 确保上传文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_data(file_path):
    """加载Excel或CSV文件"""
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    else:
        return pd.read_excel(file_path)

def preprocess_data(data, standardization, missing_value):
    """数据预处理"""
    # 处理缺失值
    if missing_value == '均值填充':
        imputer = SimpleImputer(strategy='mean')
        data = pd.DataFrame(imputer.fit_transform(data), columns=data.columns)
    elif missing_value == '中位数填充':
        imputer = SimpleImputer(strategy='median')
        data = pd.DataFrame(imputer.fit_transform(data), columns=data.columns)
    elif missing_value == '删除行':
        data = data.dropna()
    elif missing_value == '删除列':
        data = data.dropna(axis=1)
    
    # 标准化
    if standardization == '标准化':
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data)
        data = pd.DataFrame(data_scaled, columns=data.columns)
    elif standardization == '归一化':
        scaler = MinMaxScaler()
        data_scaled = scaler.fit_transform(data)
        data = pd.DataFrame(data_scaled, columns=data.columns)
    
    return data

def perform_pca_analysis(data, n_components=None, explained_variance_ratio=0.95, random_state=42):
    """执行PCA分析"""
    # 确定主成分数量
    if n_components is None:
        # 根据解释方差比例确定主成分数量
        pca_temp = PCA(random_state=random_state)
        pca_temp.fit(data)
        cumulative_variance = np.cumsum(pca_temp.explained_variance_ratio_)
        n_components = np.argmax(cumulative_variance >= explained_variance_ratio) + 1
    
    # 执行PCA
    pca = PCA(n_components=n_components, random_state=random_state)
    pca_result = pca.fit_transform(data)
    
    # 计算特征重要性（基于主成分的系数）
    feature_importance = []
    for i, feature in enumerate(data.columns):
        importance = np.mean([abs(pca.components_[j][i]) for j in range(n_components)])
        feature_importance.append({
            'name': feature,
            'importance': round(importance, 4)
        })
    
    # 按重要性排序
    feature_importance.sort(key=lambda x: x['importance'], reverse=True)
    
    return {
        'pca_result': pca_result,
        'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
        'cumulative_variance': np.cumsum(pca.explained_variance_ratio_).tolist(),
        'components': pca.components_.tolist(),
        'feature_importance': feature_importance[:10],  # 只返回前10个
        'n_components': n_components,
        'n_features': data.shape[1]
    }

@pca_bp.route('/api/pca/upload', methods=['POST'])
def upload_file():
    """上传文件接口"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有文件被上传'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            file.save(file_path)
            
            # 读取数据并生成预览
            try:
                data = load_data(file_path)
                preview = data.head(6).values.tolist()  # 前6行（包括标题）
                
                return jsonify({
                    'success': True,
                    'data': {
                        'filename': unique_filename,
                        'preview': preview,
                        'rows': data.shape[0],
                        'columns': data.shape[1]
                    }
                })
            except Exception as e:
                return jsonify({'success': False, 'message': f'文件读取失败: {str(e)}'})
        
        return jsonify({'success': False, 'message': '不支持的文件格式'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})

@pca_bp.route('/api/pca/analyze', methods=['POST'])
def analyze_data():
    """PCA分析接口"""
    try:
        data = request.get_json()
        
        # 获取参数
        filename = data.get('filename')
        standardization = data.get('standardization', '标准化')
        missing_value = data.get('missingValue', '均值填充')
        n_components = data.get('nComponents')
        explained_variance_ratio = data.get('explainedVarianceRatio', 0.95)
        random_state = data.get('randomState', 42)
        generate_plots = data.get('generatePlots', True)
        save_intermediate = data.get('saveIntermediate', False)
        
        # 加载数据
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '文件不存在'})
        
        raw_data = load_data(file_path)
        
        # 数据预处理
        processed_data = preprocess_data(raw_data, standardization, missing_value)
        
        # 执行PCA分析
        analysis_result = perform_pca_analysis(
            processed_data, 
            n_components, 
            explained_variance_ratio, 
            random_state
        )
        
        # 生成分析ID
        analysis_id = str(uuid.uuid4())
        
        # 保存分析结果
        result_data = {
            'analysis_id': analysis_id,
            'timestamp': datetime.now().isoformat(),
            'parameters': {
                'standardization': standardization,
                'missing_value': missing_value,
                'n_components': n_components,
                'explained_variance_ratio': explained_variance_ratio,
                'random_state': random_state
            },
            'results': analysis_result
        }
        
        # 保存到临时文件
        result_file = os.path.join(UPLOAD_FOLDER, f"{analysis_id}_results.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        # 准备返回数据
        response_data = {
            'analysisId': analysis_id,
            'nFeatures': analysis_result['n_features'],
            'nComponents': analysis_result['n_components'],
            'explainedVarianceRatio': round(analysis_result['explained_variance_ratio'][0], 4),
            'cumulativeVariance': round(analysis_result['cumulative_variance'][-1], 4),
            'componentContributions': [round(ratio * 100, 2) for ratio in analysis_result['explained_variance_ratio']],
            'featureImportance': analysis_result['feature_importance']
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'分析失败: {str(e)}'})

@pca_bp.route('/api/pca/download', methods=['POST'])
def download_results():
    """下载分析结果接口"""
    try:
        data = request.get_json()
        analysis_id = data.get('analysisId')
        
        if not analysis_id:
            return jsonify({'success': False, 'message': '缺少分析ID'})
        
        # 查找结果文件
        result_file = os.path.join(UPLOAD_FOLDER, f"{analysis_id}_results.json")
        if not os.path.exists(result_file):
            return jsonify({'success': False, 'message': '分析结果不存在'})
        
        # 读取分析结果
        with open(result_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建Excel文件
            excel_file = os.path.join(temp_dir, f"PCA_Analysis_{analysis_id[:8]}.xlsx")
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # 分析摘要
                summary_data = {
                    '指标': ['原始特征数', '主成分数', '解释方差比例', '累计解释方差'],
                    '值': [
                        analysis_data['results']['n_features'],
                        analysis_data['results']['n_components'],
                        round(analysis_data['results']['explained_variance_ratio'][0], 4),
                        round(analysis_data['results']['cumulative_variance'][-1], 4)
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='分析摘要', index=False)
                
                # 主成分贡献度
                pc_data = []
                for i, ratio in enumerate(analysis_data['results']['explained_variance_ratio']):
                    pc_data.append({
                        '主成分': f'PC{i+1}',
                        '解释方差比例': round(ratio, 4),
                        '累计解释方差': round(analysis_data['results']['cumulative_variance'][i], 4)
                    })
                pd.DataFrame(pc_data).to_excel(writer, sheet_name='主成分贡献度', index=False)
                
                # 特征重要性
                feature_data = []
                for feature in analysis_data['results']['feature_importance']:
                    feature_data.append({
                        '特征名称': feature['name'],
                        '重要性': feature['importance']
                    })
                pd.DataFrame(feature_data).to_excel(writer, sheet_name='特征重要性', index=False)
                
                # 主成分系数
                components_data = []
                for i, component in enumerate(analysis_data['results']['components']):
                    for j, coef in enumerate(component):
                        components_data.append({
                            '主成分': f'PC{i+1}',
                            '特征': f'Feature{j+1}',
                            '系数': round(coef, 4)
                        })
                pd.DataFrame(components_data).to_excel(writer, sheet_name='主成分系数', index=False)
            
            # 返回文件
            return send_file(
                excel_file,
                as_attachment=True,
                download_name=f"PCA_Analysis_{analysis_id[:8]}.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'})

@pca_bp.route('/api/pca/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'success': True,
        'message': 'PCA服务正常运行',
        'timestamp': datetime.now().isoformat()
    }) 