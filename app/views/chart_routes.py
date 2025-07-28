# app/views/chart_routes.py
# 图表相关API路由

from flask import Blueprint, request, jsonify
import pandas as pd
import numpy as np
import io
import base64
from werkzeug.utils import secure_filename
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

chart_bp = Blueprint('chart', __name__, url_prefix='/api/chart')

@chart_bp.route('/parse-excel', methods=['POST'])
def parse_excel():
    """
    解析Excel文件API
    支持 .xlsx, .xls, .csv 格式
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        # 获取文件扩展名
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        # 检查文件格式
        if file_ext not in ['.xlsx', '.xls', '.csv']:
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式: {file_ext}'
            }), 400
        
        # 检查文件大小 (10MB限制)
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()  # 获取文件大小
        file.seek(0)  # 重置到文件开头
        
        if file_size == 0:
            return jsonify({
                'success': False,
                'error': '文件为空'
            }), 400
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({
                'success': False,
                'error': '文件大小超过10MB限制'
            }), 400
        
        logger.info(f"开始解析文件: {filename}, 扩展名: {file_ext}, 大小: {file_size} bytes")
        
        # 根据文件类型解析
        if file_ext in ['.xlsx', '.xls']:
            result = parse_excel_file(file)
        elif file_ext == '.csv':
            result = parse_csv_file(file)
        else:
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式: {file_ext}'
            }), 400
        
        logger.info(f"文件解析成功，数据行数: {len(result['data'])}")
        
        # 验证返回数据的完整性
        if not result.get('headers') or not result.get('data'):
            return jsonify({
                'success': False,
                'error': '解析结果不完整'
            }), 500
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"解析Excel文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'解析失败: {str(e)}'
        }), 500

def parse_excel_file(file):
    """
    解析Excel文件(.xlsx, .xls)
    """
    try:
        # 尝试使用不同的引擎读取Excel文件
        engines = ['openpyxl', 'xlrd']
        
        for engine in engines:
            try:
                logger.info(f"尝试使用 {engine} 引擎读取Excel文件")
                
                # 读取Excel文件 - pandas.read_excel不支持encoding参数
                df = pd.read_excel(
                    file,
                    engine=engine
                )
                
                # 清理数据
                df = clean_dataframe(df)
                
                # 转换为列表格式
                headers = df.columns.tolist()
                data = df.values.tolist()
                
                logger.info(f"Excel文件解析成功，使用引擎: {engine}")
                return {
                    'headers': headers,
                    'data': data,
                    'engine': engine
                }
                
            except Exception as e:
                logger.warning(f"使用 {engine} 引擎读取失败: {str(e)}")
                continue
        
        # 如果所有引擎都失败，抛出异常
        raise Exception("所有Excel引擎都无法读取文件")
        
    except Exception as e:
        logger.error(f"Excel文件解析失败: {str(e)}")
        raise Exception(f"Excel文件解析失败: {str(e)}")

def parse_csv_file(file):
    """
    解析CSV文件
    """
    try:
        # 尝试多种编码和分隔符
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5']
        separators = [',', '\t', ';', '|']
        
        for encoding in encodings:
            for separator in separators:
                try:
                    logger.info(f"尝试使用 {encoding} 编码和 {separator} 分隔符读取CSV文件")
                    
                    # 重置文件指针
                    file.seek(0)
                    
                    # 读取CSV文件
                    df = pd.read_csv(
                        file,
                        encoding=encoding,
                        sep=separator,
                        engine='python'
                    )
                    
                    # 清理数据
                    df = clean_dataframe(df)
                    
                    # 转换为列表格式
                    headers = df.columns.tolist()
                    data = df.values.tolist()
                    
                    logger.info(f"CSV文件解析成功，使用编码: {encoding}, 分隔符: {separator}")
                    return {
                        'headers': headers,
                        'data': data,
                        'encoding': encoding,
                        'separator': separator
                    }
                    
                except Exception as e:
                    logger.warning(f"使用 {encoding} 编码和 {separator} 分隔符读取失败: {str(e)}")
                    continue
        
        # 如果所有组合都失败，尝试使用pandas的自动检测
        logger.info("尝试使用pandas自动检测读取CSV文件")
        try:
            file.seek(0)  # 重置文件指针
            df = pd.read_csv(file, engine='python')
            
            df = clean_dataframe(df)
            headers = df.columns.tolist()
            data = df.values.tolist()
            
            return {
                'headers': headers,
                'data': data,
                'encoding': 'auto',
                'separator': 'auto'
            }
        except Exception as e:
            logger.error(f"pandas自动检测也失败: {str(e)}")
            raise Exception("无法解析CSV文件，请检查文件格式和编码")
        
    except Exception as e:
        logger.error(f"CSV文件解析失败: {str(e)}")
        raise Exception(f"CSV文件解析失败: {str(e)}")

def clean_dataframe(df):
    """
    清理DataFrame数据
    """
    try:
        # 检查DataFrame是否为空
        if df.empty:
            raise Exception("文件内容为空")
        
        # 删除完全为空的行和列
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # 再次检查是否为空
        if df.empty:
            raise Exception("清理后文件内容为空")
        
        # 填充NaN值
        df = df.fillna('')
        
        # 智能处理数据类型
        for col in df.columns:
            try:
                # 先尝试转换为数值类型
                numeric_values = pd.to_numeric(df[col], errors='coerce')
                # 如果大部分值都是数字，则使用数字类型
                if numeric_values.notna().sum() > len(df) * 0.5:
                    df[col] = numeric_values.fillna('').astype(str)
                else:
                    df[col] = df[col].astype(str)
            except Exception as e:
                logger.warning(f"处理列 {col} 时出错: {str(e)}")
                # 如果转换失败，保持字符串类型
                df[col] = df[col].astype(str)
        
        # 确保所有值都是字符串类型，避免JSON序列化问题
        for col in df.columns:
            df[col] = df[col].astype(str)
        
        return df
        
    except Exception as e:
        logger.error(f"清理DataFrame失败: {str(e)}")
        raise Exception(f"数据处理失败: {str(e)}")

@chart_bp.route('/health', methods=['GET'])
def health_check():
    """
    图表服务健康检查
    """
    return jsonify({
        'success': True,
        'message': '图表服务正常运行',
        'services': {
            'excel_parsing': 'available',
            'pandas': 'available',
            'openpyxl': 'available'
        }
    })

@chart_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """
    获取支持的文件格式
    """
    return jsonify({
        'success': True,
        'formats': [
            {
                'extension': '.xlsx',
                'name': 'Excel 2007+',
                'description': '现代Excel格式，推荐使用'
            },
            {
                'extension': '.xls',
                'name': 'Excel 97-2003',
                'description': '旧版Excel格式，支持有限'
            },
            {
                'extension': '.csv',
                'name': 'CSV文件',
                'description': '通用文本格式，兼容性最好'
            }
        ],
        'max_file_size': '10MB',
        'encoding_support': ['UTF-8', 'GBK', 'GB2312', 'Big5']
    }) 