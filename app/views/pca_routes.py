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

# 自定义JSON编码器处理NumPy类型
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super(NumpyEncoder, self).default(obj)

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
    
    # 计算综合得分
    # 方法1：基于第一主成分的简单算法
    first_component_weights = pca.components_[0]
    
    # 方法2：基于解释方差比例的加权算法（更标准）
    # 综合得分 = Σ(主成分得分 × 解释方差比例)
    comprehensive_scores = []
    for i, sample in enumerate(pca_result):
        # 简单算法：使用第一主成分得分
        simple_score = sample[0]
        
        # 标准算法：加权综合得分
        weighted_score = 0
        for j, pc_score in enumerate(sample):
            weighted_score += pc_score * pca.explained_variance_ratio_[j]
        
        comprehensive_scores.append({
            'sample_index': i,
            'sample_name': f'Sample_{i+1}',  # 默认样本名称
            'simple_score': round(simple_score, 6),  # 简单算法得分
            'weighted_score': round(weighted_score, 6),  # 加权算法得分
            'principal_component_scores': sample.tolist()
        })
    
    # 按加权综合得分排序（更标准）
    comprehensive_scores.sort(key=lambda x: x['weighted_score'], reverse=True)
    
    # 添加排名
    for i, score_item in enumerate(comprehensive_scores):
        score_item['ranking'] = i + 1
    
    # 计算权重（基于第一主成分系数）
    total_weight = sum(abs(first_component_weights))
    feature_weights = []
    for i, feature in enumerate(data.columns):
        weight_percentage = (abs(first_component_weights[i]) / total_weight) * 100
        feature_weights.append({
            'name': feature,
            'coefficient': round(first_component_weights[i], 4),
            'weight_percentage': round(weight_percentage, 2)
        })
    
    # 按权重排序
    feature_weights.sort(key=lambda x: x['weight_percentage'], reverse=True)
    
    return {
        'pca_result': pca_result.tolist(),  # 转换为列表
        'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
        'cumulative_variance': np.cumsum(pca.explained_variance_ratio_).tolist(),
        'components': pca.components_.tolist(),
        'feature_importance': feature_importance[:10],  # 只返回前10个
        'feature_weights': feature_weights,  # 新增：特征权重
        'comprehensive_scores': comprehensive_scores,  # 新增：综合得分
        'n_components': int(n_components),  # 确保是整数
        'n_features': int(data.shape[1])  # 确保是整数
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
                
                # 生成预览数据：包含列名和前5行数据
                headers = data.columns.tolist()
                preview_data = data.head(5).values.tolist()
                
                # 如果列数太多，只显示前20列，并添加提示
                max_columns = 20
                if len(headers) > max_columns:
                    headers = headers[:max_columns]
                    preview_data = [row[:max_columns] for row in preview_data]
                    preview = [headers] + preview_data
                    # 添加列数提示
                    preview.append([f"（仅显示前{max_columns}列，共{data.shape[1]}列）"])
                else:
                    preview = [headers] + preview_data  # 第一行是列名，后面是数据
                
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
            json.dump(result_data, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
        
        # 准备返回数据
        response_data = {
            'analysisId': analysis_id,
            'nFeatures': analysis_result['n_features'],
            'nComponents': analysis_result['n_components'],
            'explainedVarianceRatio': round(analysis_result['explained_variance_ratio'][0], 4),
            'cumulativeVariance': round(analysis_result['cumulative_variance'][-1], 4),
            'componentContributions': [round(ratio * 100, 2) for ratio in analysis_result['explained_variance_ratio']],
            'featureImportance': analysis_result['feature_importance'],
            'featureWeights': analysis_result['feature_weights'],  # 新增：特征权重
            'comprehensiveScores': analysis_result['comprehensive_scores']  # 新增：综合得分
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
                
                # 特征权重（对应图片表3）
                weights_data = []
                for weight in analysis_data['results']['feature_weights']:
                    weights_data.append({
                        '特征名称': weight['name'],
                        '主成分1系数': weight['coefficient'],
                        '权重百分比': f"{weight['weight_percentage']}%"
                    })
                pd.DataFrame(weights_data).to_excel(writer, sheet_name='特征权重', index=False)
                
                # 综合得分及排序（对应图片表4）
                scores_data = []
                for score in analysis_data['results']['comprehensive_scores']:
                    scores_data.append({
                        '样本名称': score['sample_name'],
                        '简单算法得分': score['simple_score'],
                        '加权算法得分': score['weighted_score'],
                        '排序': score['ranking']
                    })
                pd.DataFrame(scores_data).to_excel(writer, sheet_name='综合得分排序', index=False)
            
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