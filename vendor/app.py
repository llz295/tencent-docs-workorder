import os
import pandas as pd
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import tempfile
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import sys
import time
import random
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from urllib.parse import urlparse, parse_qs
import json
try:
    from fake_useragent import UserAgent
except ImportError:
    UserAgent = None
import io

import requests
import json as json_module

# 配置日志
import logging
from logging.handlers import RotatingFileHandler

# 不使用静态文件夹
app = Flask(__name__, template_folder='templates', static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = 100 * 10024 * 1024  # 100MB max file size

# 设置日志
if not app.debug:
    file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('应用启动')

# 存储处理结果的全局变量
app.config['OUTPUT_FILE_PATH'] = None
app.config['OUTPUT_FILE_NAME'] = None

# 确保templates目录存在
os.makedirs('templates', exist_ok=True)

# 默认配置
DEFAULT_CONFIG = {
    'name': '默认催收智能体'
}

# 题型模板文件
TEMPLATES_FILE = "question_templates.json"

def _voice_actor_config_path():
    """tencent_docs_pom/data/voice_actor_config.json（开发与打包共用）。"""
    from pathlib import Path

    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / "data" / "voice_actor_config.json")
    candidates.append(
        Path(__file__).resolve().parent / "tencent_docs_pom" / "data" / "voice_actor_config.json"
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _load_voice_actor_config():
    path = _voice_actor_config_path()
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_voice_actor_mapping():
    """获取录音师映射关系（优先读 voice_actor_config.json）。"""
    cfg = _load_voice_actor_config()
    if cfg and isinstance(cfg.get("name_mapping"), dict):
        return {str(k): str(v) for k, v in cfg["name_mapping"].items()}
    return {"译可易": "译可易"}


def get_voice_actor_prices():
    """获取录音师价格信息（优先读 voice_actor_config.json）。"""
    cfg = _load_voice_actor_config()
    if cfg and isinstance(cfg.get("prices"), dict):
        return cfg["prices"]
    return {}

def get_voice_actor_tax_info():
    """获取录音师税务信息"""
    return {
        "毛慧": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "王希爱": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "边静": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "狄梦一": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "尤含": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "郝晓芹": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "孙小雨": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "刘施彤": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "高代容": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "任冉微": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "胡冬柏": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "刘文": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "费雅静": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "汪昊": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "史慧霞": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "袁裕婷": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "李宏宇": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "杨易达": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "张慧": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "程若琪": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "姚梦茹": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "贾环旭": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "蒋英": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "杨海晨": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "罗永康": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "焦鹏": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        },
        "译可易": {
            "证件类型": "",
            "证件号码": "",
            "银行信息": "",
            "发薪卡号": "",
            "手机号码": "",
            "入职时间": ""
        }
    }

def calculate_tax_info(after_tax):
    """根据税后金额计算个税和税前金额"""
    try:
        after_tax = float(after_tax)
        # 个税计算公式
        if after_tax <= 800:
            tax = 0
        elif after_tax <= 3360:
            tax = (after_tax - 800) / 4
        elif after_tax <= 21000:
            tax = 0.16 * after_tax / 0.84
        elif after_tax <= 49500:
            tax = (0.24 * after_tax - 2000) / 0.76
        else:
            tax = (0.32 * after_tax - 7000) / 0.68
        
        # 税前金额 = 税后金额 + 个税
        before_tax = after_tax + tax
        
        return round(tax, 2), round(before_tax, 2)
    except (ValueError, TypeError):
        return 0.0, 0.0

def compare_texts_detailed(std_text, match_text):
    """详细比较两个文本的差异，返回具体的差异说明"""
    # 清理文本
    def clean_text_for_comparison(text):
        if pd.isna(text):
            return ""
        text_str = str(text).strip()
        # 移除空白字符
        import re
        text_str = re.sub(r'\s+', '', text_str, flags=re.UNICODE)
        # 移除零宽字符
        text_str = re.sub(r'[\u200B-\u200D\uFEFF]', '', text_str)
        # 移除标点符号（保留中文、英文、数字）
        text_str = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text_str)
        return text_str
    
    std_clean = clean_text_for_comparison(std_text)
    match_clean = clean_text_for_comparison(match_text)
    
    # 如果文本相同，返回空
    if std_clean == match_clean:
        return ""
    
    # 找出具体差异
    diff_details = []
    
    # 检查是否有完全包含关系
    if std_clean in match_clean and len(std_clean) < len(match_clean):
        # 待匹配文本包含了标准文本
        extra_text = match_clean.replace(std_clean, "")
        if extra_text:
            diff_details.append(f"待匹配表多了文本: {extra_text}")
    elif match_clean in std_clean and len(match_clean) < len(std_clean):
        # 标准文本包含了待匹配文本
        missing_text = std_clean.replace(match_clean, "")
        if missing_text:
            diff_details.append(f"待匹配表少了文本: {missing_text}")
    else:
        # 没有包含关系，找出不同的部分
        # 这里我们简单地说明两个文本不一致
        diff_details.append("文本内容不一致")
        
        # 可以进一步分析具体的字符差异
        if len(std_clean) != len(match_clean):
            if len(std_clean) > len(match_clean):
                diff_details.append(f"待匹配表少了{len(std_clean) - len(match_clean)}个字符")
            else:
                diff_details.append(f"待匹配表多了{len(match_clean) - len(std_clean)}个字符")
    
    return "; ".join(diff_details)

def map_voice_actor(original_name):
    """映射录音师名称"""
    mapping = get_voice_actor_mapping()
    return mapping.get(str(original_name).strip(), str(original_name).strip())

# 表单「录音类型/录音规格」取值（新名 + 旧名兼容）
_FULL_SPEC_TYPES = frozenset({"全新", "整套"})
_SUPPLEMENT_SPEC_TYPES = frozenset({"补录", "新增"})


def _norm_spec_type(spec_type) -> str:
    return str(spec_type).strip()


def calculate_price(voice_actor, spec_type, count):
    """计算录音价格"""
    prices = get_voice_actor_prices()
    if voice_actor not in prices:
        return 0

    spec = _norm_spec_type(spec_type)
    if spec in _FULL_SPEC_TYPES:
        return prices[voice_actor]["full_price"]
    elif spec in _SUPPLEMENT_SPEC_TYPES:
        try:
            return prices[voice_actor]["supplement_price"] * float(count)
        except (ValueError, TypeError):
            return 0
    return 0

def fix_excel_file_style(file_content):
    """修复Excel文件中的样式问题"""
    try:
        # 读取文件内容
        if hasattr(file_content, 'getvalue'):
            file_data = file_content.getvalue()
        else:
            file_content.seek(0)
            file_data = file_content.read()
        
        # 创建内存中的ZIP文件
        with zipfile.ZipFile(BytesIO(file_data), 'r') as zip_ref:
            # 获取所有文件列表
            file_list = zip_ref.namelist()
            
            # 创建新的ZIP文件
            new_zip_buffer = BytesIO()
            with zipfile.ZipFile(new_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                for file_name in file_list:
                    # 读取文件内容
                    file_content_data = zip_ref.read(file_name)
                    
                    # 如果是样式文件，替换为简单样式
                    if 'styles.xml' in file_name:
                        # 生成简单的样式文件
                        new_styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="0"/>
<fonts count="1">
<font>
<sz val="11"/>
<color theme="1"/>
<name val="Calibri"/>
<family val="2"/>
<scheme val="minor"/>
</font>
</fonts>
<fills count="2">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
</fills>
<borders count="1">
<border>
<left/>
<right/>
<top/>
<bottom/>
<diagonal/>
</border>
</borders>
<cellStyleXfs count="1">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
</cellStyleXfs>
<cellXfs count="1">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
</cellXfs>
<cellStyles count="1">
<cellStyle name="Normal" xfId="0" builtinId="0"/>
</cellStyles>
<dxfs count="0"/>
<tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>
</styleSheet>'''
                        new_zip.writestr(file_name, new_styles)
                    else:
                        # 其他所有文件都直接写入（不删除任何数据）
                        new_zip.writestr(file_name, file_content_data)
                        new_zip.writestr(file_name, file_content_data)
            
            # 返回修复后的文件内容
            new_zip_buffer.seek(0)
            return BytesIO(new_zip_buffer.read())
        
    except Exception as e:
        print(f"修复Excel文件样式失败: {str(e)}")
        # 如果修复失败，返回原始文件
        if hasattr(file_content, 'seek'):
            file_content.seek(0)
        return file_content

def read_excel_with_data_only(file_content, header_row=1, sheet_name=None):
    """使用pandas读取Excel数据，确保读取所有列"""
    try:
        # 使用pandas读取，确保读取所有列
        if sheet_name:
            df = pd.read_excel(file_content, header=header_row, sheet_name=sheet_name, engine='openpyxl')
        else:
            df = pd.read_excel(file_content, header=header_row, engine='openpyxl')
        
        print(f"使用pandas读取成功，列数: {len(df.columns)}, 行数: {len(df)}")
        return df
    except Exception as e:
        print(f"使用pandas读取失败: {e}")
        # 如果pandas读取失败，回退到openpyxl手动读取
        # 使用openpyxl加载工作簿，只读数据
        wb = load_workbook(file_content, data_only=True, read_only=True)
        
        # 选择工作表
        if sheet_name:
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
            else:
                wb.close()
                raise ValueError(f"工作表 '{sheet_name}' 不存在")
        else:
            ws = wb.active
        
        if ws is None:
            wb.close()
            raise ValueError("无法获取工作表")
        
        # 手动读取数据，确保读取所有列
        data = []
        max_cols = 0
        
        # 先确定最大列数
        for row in ws.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                max_cols = max(max_cols, len(row))
        
        # 再读取所有数据
        for row in ws.iter_rows(values_only=True):
            # 检查这一行是否包含任何非空数据
            if any(cell is not None for cell in row):
                # 确保行数据长度一致
                if len(row) < max_cols:
                    # 用None填充到最大列数
                    padded_row = list(row) + [None] * (max_cols - len(row))
                    data.append(padded_row)
                else:
                    data.append(list(row))
        
        print(f"读取到的原始数据行数: {len(data)}")
        print(f"最大列数: {max_cols}")
        
        if len(data) <= header_row:
            wb.close()
            raise ValueError(f"文件数据不足，无法获取第{header_row+1}行作为表头")
        
        # 根据实际情况，header_row=1表示使用第二行作为列名
        if header_row == 1 and len(data) > 1:
            # 使用第二行作为列名
            columns = [str(cell) if cell is not None else f'Col_{i}' for i, cell in enumerate(data[1])]
            # 数据从第三行开始
            df_data = data[2:] if len(data) > 2 else []
        else:
            # 默认使用第一行作为列名
            columns = [str(cell) if cell is not None else f'Col_{i}' for i, cell in enumerate(data[0])]
            # 数据从第二行开始
            df_data = data[1:] if len(data) > 1 else []
        
        print(f"列名: {columns}")
        print(f"数据行数: {len(df_data)}")
        print(f"列数: {len(columns)}")
        
        # 创建 DataFrame，确保使用所有列
        if df_data:
            df = pd.DataFrame(df_data, columns=pd.Index(columns, dtype=object))
        else:
            df = pd.DataFrame(columns=pd.Index(columns, dtype=object))
        
        print(f"创建的DataFrame行数: {len(df)}, 列数: {len(df.columns)}")
        wb.close()
        return df

def read_excel_file(file_content, target_columns, sheet_name=None):
    """读取Excel文件，尝试不同引擎并匹配目标列"""
    # 首先尝试不同的读取策略（只读数据，不读格式）
    # 根据您的说明，数据表前两行是表头，第二行作为列名
    read_strategies = [
        # 策略1: openpyxl 只读数据，使用第二行作为表头
        lambda f: read_excel_with_data_only(f, header_row=1, sheet_name=sheet_name),
        # 策略2: openpyxl 普通读取，使用第二行作为表头
        lambda f: pd.read_excel(f, engine='openpyxl', header=1, sheet_name=sheet_name) if sheet_name else pd.read_excel(f, engine='openpyxl', header=1),
        # 策略3: 使用header=0然后手动处理（如果需要第一行作为表头）
        lambda f: read_excel_with_data_only(f, header_row=0, sheet_name=sheet_name),
        # 策略4: xlrd引擎 (适用于.xls文件)
        lambda f: pd.read_excel(f, engine='xlrd', header=1, sheet_name=sheet_name) if sheet_name else pd.read_excel(f, engine='xlrd', header=1),
        # 策略5: 默认引擎
        lambda f: pd.read_excel(f, header=1, sheet_name=sheet_name) if sheet_name else pd.read_excel(f, header=1),
        # 策略6: 使用calamine引擎 (更可靠的Excel读取)
        lambda f: pd.read_excel(f, engine='calamine', header=1, sheet_name=sheet_name) if sheet_name else pd.read_excel(f, engine='calamine', header=1),
    ]
    
    df = None
    used_strategy = None
    
    for i, strategy in enumerate(read_strategies):
        try:
            # 重置文件指针位置
            if hasattr(file_content, 'seek'):
                file_content.seek(0)
            
            df = strategy(file_content)
            used_strategy = i + 1
            
            # 验证数据是否有效
            if df is not None and not df.empty:
                # 如果使用的header=0，检查是否需要手动处理表头
                if i == 2:  # 策略3
                    unnamed_count = sum(1 for col in df.columns if 'Unnamed' in str(col))
                    if unnamed_count > len(df.columns) * 0.5:
                        # 手动设置表头为第一行的数据
                        if len(df) > 0:
                            new_columns = [str(val) if pd.notna(val) else f'Column_{j}' for j, val in enumerate(df.iloc[0])]
                            df = df.iloc[1:].copy()
                            df.columns = pd.Index(new_columns, dtype=object)
            
            print(f"成功使用策略{used_strategy}读取文件，列数: {len(df.columns)}")
            break
            
        except Exception as e:
            # 如果是样式相关的错误，尝试修复
            if "expected <class 'openpyxl.styles.fills.Fill'>" in str(e):
                print(f"策略{i+1}失败，检测到样式问题，尝试修复...")
                try:
                    # 修复样式问题
                    file_content = fix_excel_file_style(file_content)
                    # 重试当前策略
                    if hasattr(file_content, 'seek'):
                        file_content.seek(0)
                    df = strategy(file_content)
                    used_strategy = i + 1
                    print(f"修复后成功使用策略{used_strategy}读取文件，列数: {len(df.columns) if df is not None else 0}")
                    break
                except Exception as fix_e:
                    print(f"修复后重试策略{i+1}仍然失败: {str(fix_e)}")
            else:
                print(f"策略{i+1}失败: {str(e)}")
            continue
    
    if df is None or df.empty:
        # 尝试最后一种策略：使用openpyxl的data_only=False
        try:
            print("尝试使用openpyxl的data_only=False模式")
            if hasattr(file_content, 'seek'):
                file_content.seek(0)
            
            wb = load_workbook(file_content, data_only=False, read_only=True)
            if sheet_name:
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                else:
                    wb.close()
                    raise ValueError(f"工作表 '{sheet_name}' 不存在")
            else:
                ws = wb.active
            
            if ws is None:
                wb.close()
                raise ValueError("无法获取工作表")
            
            # 手动读取数据，使用第二行作为表头
            data = []
            for row in ws.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    data.append(row)
            
            if len(data) > 2:  # 确保至少有3行数据（两行表头+数据）
                columns = [str(cell) if cell is not None else f'Col_{i}' for i, cell in enumerate(data[1])]  # 第二行作为列名
                df_data = data[2:]  # 从第三行开始是数据
                df = pd.DataFrame(df_data, columns=pd.Index(columns, dtype=object))
                print("使用openpyxl的data_only=False模式成功读取文件")
            
            wb.close()
        except Exception as e:
            print(f"使用openpyxl的data_only=False模式也失败: {str(e)}")
    
    if df is None or df.empty:
        raise Exception(f"所有策略都失败，无法读取文件")
    
    # 预处理数据：清理空行和全空列
    df = df.dropna(how='all')  # 删除全空行
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]  # 删除Unnamed列
    
    # 如果数据框为空，尝试使用不同的header参数
    if df.empty or len(df) == 0:
        print("数据框为空，尝试使用header=0重新读取")
        try:
            # 重置文件指针位置
            if hasattr(file_content, 'seek'):
                file_content.seek(0)
            df = pd.read_excel(file_content, header=0, sheet_name=sheet_name) if sheet_name else pd.read_excel(file_content, header=0)
            df = df.dropna(how='all')
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        except Exception as e:
            print(f"使用header=0重新读取也失败: {str(e)}")
    
    df = process_datetime_columns(df)

    # 提取原始列名并清理空格等干扰
    original_cols = [str(col).strip() for col in df.columns]
    # 构建原始列到目标列的映射（根据用户规定的字段对应关系）
    col_mapping = {}
    
    # 字段映射规则
    field_mapping_rules = {
        "日期": ["提交时间", "日期", "时间", "Date", "date", "时间戳"],
        "编号": ["编号", "ID", "id", "序号", "No.", "NO"],
        "需求人": ["提交人", "需求人", "申请人", "用户"],
        "发起部门": [],  # 固定为"信贷业务部"
        "项目名称": ["项目【中文】", "项目名称", "项目", "标题"],
        "需求场景描述": ["需求场景描述", "场景描述", "描述", "需求描述"],
        "服务重要性等级": ["服务重要性等级", "重要性等级", "优先级", "优先级等级", "重要程度"],
        "机器人任务名称": ["话术名称", "任务名称", "机器人任务名称", "机器人任务"],
        "录音师": ["录音师", "配音师"],
        "录音条数": ["录音句数", "录音条数", "句数", "条数"],
        "录音规格": ["录音类型", "录音规格", "规格"],
        "期望完成时间": ["期望交付时间", "期望完成时间", "预计完成时间", "交付时间"],
        "录音价格": ["录音价格", "价格", "费用"],
        "是否已协调": ["是否已协调", "协调状态", "协调情况"],
        "预计完成时间": ["预计完成时间", "预估完成时间"],
        "备注": ["录音效果备注", "备注", "说明"],
        "需求是否完结": ["进度", "需求是否完结", "完成状态"]
    }
    
    for target_col in target_columns:
        col_mapping[target_col] = None
        
        # 特殊处理发起部门，固定为"信贷业务部"
        if target_col == "发起部门":
            col_mapping[target_col] = "固定값"  # 特殊标记
            continue
        
        # 根据映射规则查找对应列
        possible_names = field_mapping_rules.get(target_col, [])
        # 添加目标列名本身作为可能的匹配项
        possible_names.append(target_col)
        
        # 遍历所有可能的列名进行匹配
        for possible_name in possible_names:
            for idx, orig_col in enumerate(original_cols):
                # 清理列名用于比较
                orig_col_clean = str(orig_col).strip().lower().replace(" ", "").replace("　", "").replace("_", "").replace("-", "")
                possible_name_clean = str(possible_name).strip().lower().replace(" ", "").replace("　", "").replace("_", "").replace("-", "")
                
                # 多种匹配方式
                if (possible_name_clean == orig_col_clean or 
                    possible_name_clean in orig_col_clean or 
                    orig_col_clean in possible_name_clean or
                    # 模糊匹配：只要包含关键词即可
                    (len(possible_name_clean) > 1 and possible_name_clean in orig_col_clean)):
                    col_mapping[target_col] = df.columns[idx]
                    print(f"列匹配成功: {target_col} <- {orig_col}")
                    break
            
            if col_mapping[target_col] is not None:
                break
        
        # 如果仍未找到匹配列，尝试更宽松的匹配
        if col_mapping[target_col] is None:
            for idx, orig_col in enumerate(original_cols):
                orig_col_clean = str(orig_col).strip().lower()
                target_col_clean = str(target_col).strip().lower()
                # 如果列名包含目标列名的关键字
                if target_col_clean in orig_col_clean or orig_col_clean in target_col_clean:
                    col_mapping[target_col] = df.columns[idx]
                    print(f"宽松匹配成功: {target_col} <- {orig_col}")
                    break
    
    # 输出列映射信息以便调试
    print(f"文件的列映射情况:")
    for target_col, orig_col in col_mapping.items():
        if orig_col is not None:
            print(f"  {target_col} -> {orig_col}")
        else:
            print(f"  {target_col} -> 未找到匹配列")
    
    # 处理每一列，有匹配则取数据，无则置空
    new_df = pd.DataFrame()
    for target_col in target_columns:
        orig_col = col_mapping[target_col]
        if orig_col == "固定값":  # 发起部门的特殊处理
            new_df[target_col] = "信贷业务部"
        elif orig_col is not None:
            new_df[target_col] = df[orig_col].fillna('')  # 填充空值
        else:
            # 如果未找到匹配列，尝试模糊匹配
            matched = False
            target_col_clean = target_col.strip().lower()
            for df_col in df.columns:
                df_col_clean = str(df_col).strip().lower()
                # 更宽松的匹配条件
                if (target_col_clean in df_col_clean or 
                    df_col_clean in target_col_clean or
                    target_col_clean.replace("名称", "") in df_col_clean or
                    df_col_clean.replace("名称", "") in target_col_clean):
                    new_df[target_col] = df[df_col].fillna('')
                    matched = True
                    print(f"模糊匹配成功: {target_col} <- {df_col}")
                    break
            
            # 如果仍未匹配成功，则置空
            if not matched:
                new_df[target_col] = ""
    
    # 特殊处理：确保关键列有数据时能正确映射
    # 如果原始数据中有"提交时间"但映射到"日期"失败，则手动处理
    try:
        if "日期" in new_df.columns:
            # 检查日期列是否为空或全为NaN
            date_series = new_df["日期"]
            is_empty = len(date_series) == 0
            is_all_na = False
            try:
                is_all_na = bool(date_series.isna().all()) if len(date_series) > 0 else True
            except:
                pass
            
            if is_empty or is_all_na:
                for col in df.columns:
                    col_str = str(col)
                    if "提交时间" in col_str or "日期" in col_str:
                        new_df["日期"] = df[col].fillna('')
                        print(f"手动映射日期列: 日期 <- {col}")
                        break
    except Exception as e:
        print(f"处理日期列时出错: {e}")
    
    # 特殊处理：确保其他关键列也能正确映射
    key_mappings = {
        "编号": ["编号", "ID", "id", "序号"],
        "需求人": ["提交人", "需求人", "申请人", "用户"],
        "录音师": ["录音师", "配音师"],
        "录音条数": ["录音句数", "录音条数", "句数", "条数"],
        "录音规格": ["录音类型", "录音规格"]
    }
    
    print(f"开始特殊处理关键列映射...")
    print(f"new_df当前行数: {len(new_df)}")
    print(f"df原始数据行数: {len(df)}")
    
    for target_col, possible_names in key_mappings.items():
        if target_col in new_df.columns:
            # 检查当前列是否为空
            is_empty = len(new_df[target_col]) == 0
            is_all_na = False
            try:
                is_all_na = bool(new_df[target_col].isna().all()) if len(new_df[target_col]) > 0 else True
            except:
                pass
            
            print(f"检查列 {target_col}: empty={is_empty}, all_na={is_all_na}")
            
            if is_empty or is_all_na:
                print(f"列 {target_col} 需要手动映射")
                # 尝试从原始数据中找到匹配的列
                for col in df.columns:
                    col_str = str(col).strip().lower()
                    for name in possible_names:
                        name_lower = name.lower()
                        if name_lower in col_str or col_str in name_lower or name_lower == col_str:
                            new_df[target_col] = df[col].fillna('')
                            print(f"手动映射关键列: {target_col} <- {col} (匹配词: {name})")
                            # 确保new_df的行数与df一致
                            if len(new_df) < len(df):
                                print(f"调整new_df行数从{len(new_df)}到{len(df)}")
                                # 重新创建DataFrame以确保行数一致
                                new_df = new_df.reindex(range(len(df)))
                            break
                    else:
                        continue
                    break
            else:
                print(f"列 {target_col} 已有数据，无需手动映射")
    
    # 处理录音师映射
    if '录音师' in new_df.columns:
        print(f"处理录音师映射前: {new_df['录音师'].tolist()}")
        new_df['录音师'] = new_df['录音师'].apply(map_voice_actor)
        print(f"处理录音师映射后: {new_df['录音师'].tolist()}")
    
    # 计算录音价格
    if '录音价格' in new_df.columns and '录音师' in new_df.columns and '录音规格' in new_df.columns and '录音条数' in new_df.columns:
        print(f"计算录音价格前各列数据:")
        print(f"  录音师: {new_df['录音师'].tolist()}")
        print(f"  录音规格: {new_df['录音规格'].tolist()}")
        print(f"  录音条数: {new_df['录音条数'].tolist()}")
        new_df['录音价格'] = new_df.apply(
            lambda row: calculate_price(
                row['录音师'], 
                row['录音规格'], 
                row['录音条数']
            ), axis=1
        )
        print(f"计算录音价格后: {new_df['录音价格'].tolist()}")
    
    # 确保在返回前处理日期列
    new_df = process_datetime_columns(new_df)
    
    return new_df

def process_datetime_columns(df):
    """处理数据框中的日期时间列，格式化为 YY/MM/DD"""
    # 更全面地识别日期时间列
    datetime_columns = []
    for col in df.columns:
        col_str = str(col)
        # 检查列名是否包含日期/时间相关关键词
        if any(keyword in col_str for keyword in ["日期", "时间", "Date", "Time", "date", "time"]):
            datetime_columns.append(col)
    
    print(f"识别到的日期时间列: {datetime_columns}")
    
    # 如果没有识别到日期列，尝试处理所有列
    if not datetime_columns:
        # 检查所有列中可能包含日期的数据
        for col in df.columns:
            # 检查列中是否有日期格式的数据
            sample_data = df[col].dropna().head(3)  # 取前3个非空值作为样本
            for val in sample_data:
                if isinstance(val, str) and ('-' in val or '/' in val):
                    # 简单检查是否可能是日期格式
                    try:
                        pd.to_datetime(val, errors='raise')
                        datetime_columns.append(col)
                        break  # 找到一个就可以认为是日期列
                    except:
                        continue
    
    print(f"最终识别的日期时间列: {datetime_columns}")
    
    for col in datetime_columns:
        try:
            # 检查列中的数据类型
            sample_values = df[col].dropna().head(5)
            print(f"列 '{col}' 的样本值: {sample_values.tolist()}")
            
            # 如果列中的值是数字（Excel日期格式），需要特殊处理
            if len(sample_values) > 0:
                first_val = sample_values.iloc[0]
                # 检查是否为数字类型（使用pandas的检查方法）
                is_numeric = pd.api.types.is_numeric_dtype(type(first_val)) or isinstance(first_val, (int, float))
                if is_numeric and first_val > 1000:  # 可能是Excel日期数字
                    # Excel日期数字转换为日期 (使用正确的origin)
                    # 注意：Excel日期数字从1900年1月1日开始计算，但有一个bug（1900年不是闰年却被当作闰年）
                    # 所以需要减去2天来补偿这个bug
                    excel_dates = pd.to_datetime(df[col] - 2, unit='D', origin='1900-01-01', errors='coerce')
                    df[col] = excel_dates
                else:
                    # 尝试转换为日期时间格式
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # 格式化为 YYYY/MM/DD
            df[col] = df[col].dt.strftime('%Y/%m/%d')
            # 填充空值
            df[col] = df[col].fillna('')
            print(f"成功处理日期列 '{col}': {df[col].head()}")
        except Exception as e:
            print(f"处理日期时间列 '{col}' 时出错: {str(e)}")
            # 如果处理失败，尝试保持原始格式
            df[col] = df[col].fillna('')
    return df

def create_settlement_summary(df):
    """创建结算汇总表"""
    summary_data = []
    prices = get_voice_actor_prices()
    
    # 按录音师分组
    for voice_actor in df['录音师'].unique():
        if pd.isna(voice_actor) or voice_actor == '':
            continue
            
        actor_data = df[df['录音师'] == voice_actor]
        
        # 统计整套/全新数量
        full_count = len(actor_data[actor_data['录音规格'].apply(_norm_spec_type).isin(_FULL_SPEC_TYPES)])
        
        # 统计新增/补录数量（按录音条数累计）
        supplement_data = actor_data[actor_data['录音规格'].apply(_norm_spec_type).isin(_SUPPLEMENT_SPEC_TYPES)]
        supplement_count = 0
        for _, row in supplement_data.iterrows():
            try:
                supplement_count += float(row['录音条数']) if pd.notna(row['录音条数']) else 0
            except (ValueError, TypeError):
                pass
        
        # 计算小计（总价格）
        total_price = 0
        for _, row in actor_data.iterrows():
            try:
                total_price += float(row['录音价格']) if pd.notna(row['录音价格']) else 0
            except (ValueError, TypeError):
                pass
        
        # 获取单价信息
        full_price = prices.get(voice_actor, {}).get('full_price', 0)
        supplement_price = prices.get(voice_actor, {}).get('supplement_price', 0)
        
        summary_data.append({
            '录音师': voice_actor,
            '整套': int(full_count),
            '新增': int(supplement_count),
            '全新单价': full_price,
            '补录单价': supplement_price,
            '小计(元)': round(total_price, 2)  # 保留两位小数
        })
    
    return pd.DataFrame(summary_data)

def create_final_table(summary_df):
    """创建终表"""
    tax_info = get_voice_actor_tax_info()
    final_data = []
    
    for _, row in summary_df.iterrows():
        voice_actor = row['录音师']
        if voice_actor in tax_info:
            actor_info = tax_info[voice_actor]
            # 计算税前税后和个税
            after_tax = row['税后']  # 税后金额来自结算汇总表的税后列
            tax, before_tax = calculate_tax_info(after_tax)
            
            final_data.append({
                '公司主体': '北京荣达天下信息科技有限公司',
                '报税类型': '非连续税务',
                '姓名': voice_actor,
                '证件类型': actor_info['证件类型'],
                '证件号码': actor_info['证件号码'],
                '税前应发金额': before_tax,
                '应纳个税': tax,
                '税后实发金额': after_tax,
                '银行信息': actor_info['银行信息'],
                '发薪卡号': actor_info['发薪卡号'],
                '手机号码': actor_info['手机号码'],
                '入职时间': actor_info['入职时间']  # 添加入职时间
            })
    
    return pd.DataFrame(final_data)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/salary')
def salary():
    return render_template('upload.html')

@app.route('/comparison')
def comparison():
    return render_template('comparison.html')

@app.route('/process', methods=['POST'])
def process_files():
    try:
        # 获取上传的文件
        files = request.files.getlist('file')
        sheet_name = request.form.get('sheet_name')
        
        if not files or not sheet_name:
            return jsonify({'success': False, 'error': '请上传文件并填写工作表名称'})
        
        # 过滤出Excel文件
        excel_files = [f for f in files if f and f.filename and f.filename.endswith(('.xlsx', '.xls'))]
        
        if not excel_files:
            return jsonify({'success': False, 'error': '请上传至少一个Excel文件 (.xlsx 或 .xls)'})
        
        target_columns = [
            "日期", "编号", "需求人", "发起部门", "项目名称", 
            "需求场景描述", "服务重要性等级", "机器人任务名称",
            "录音师", "录音条数", "录音规格", "期望完成时间", 
            "录音价格", "是否已协调", "预计完成时间", "备注",
            "需求是否完结"
        ]
        
        processed_files = []
        error_files = []
        
        # 添加录音师状态跟踪
        voice_actor_status = {
            "success": set(),  # 读取成功的录音师
            "failed": set(),   # 读取失败的录音师
            "no_data": set()   # 无数据的录音师
        }
        
        # 添加详细的错误分类
        error_details = {
            "read_error": [],    # 读取异常
            "no_data": [],       # 无数据
            "other_error": []    # 其他错误
        }
        
        for file in excel_files:
            try:
                # 读取文件内容
                file_content = io.BytesIO(file.read())
                df = read_excel_file(file_content, target_columns, sheet_name)
                processed_files.append((file.filename, df))
                print(f"已处理文件: {file.filename}")
                
                # 更新录音师状态 - 成功读取的录音师
                if '录音师' in df.columns:
                    success_actors = df['录音师'][df['录音师'].notna() & (df['录音师'] != '')].unique().tolist()
                    voice_actor_status["success"].update(success_actors)
            except Exception as e:
                error_files.append((file.filename, str(e)))
                print(f"处理文件 {file.filename} 时出错: {str(e)}")
                
                # 分类错误类型
                error_msg = str(e).lower()
                if "expected <class 'openpyxl.styles.fills.fill'>" in error_msg or "cannot read" in error_msg or "invalid" in error_msg:
                    error_details["read_error"].append((file.filename, str(e)))
                elif "empty" in error_msg or "no data" in error_msg or "数据不足" in error_msg:
                    error_details["no_data"].append((file.filename, str(e)))
                else:
                    error_details["other_error"].append((file.filename, str(e)))
        
        if not processed_files:
            # 构建详细的错误信息
            error_info = "没有成功处理的文件\n\n"
            if error_details["read_error"]:
                error_info += "读取异常文件:\n"
                for filename, error in error_details["read_error"]:
                    error_info += f"  - {filename}: {error}\n"
                error_info += "\n"
            
            if error_details["no_data"]:
                error_info += "无数据文件:\n"
                for filename, error in error_details["no_data"]:
                    error_info += f"  - {filename}: {error}\n"
                error_info += "\n"
            
            if error_details["other_error"]:
                error_info += "其他错误文件:\n"
                for filename, error in error_details["other_error"]:
                    error_info += f"  - {filename}: {error}\n"
            
            return jsonify({'success': False, 'error': error_info})
        
        # 合并所有数据
        all_data = pd.concat([df for (file, df) in processed_files], ignore_index=True)
        all_data = all_data[target_columns]
        
        # 数据清理：删除全空行
        all_data = all_data.dropna(how='all')
        
        # 更新录音师状态 - 无数据的录音师
        if '录音师' in all_data.columns:
            # 使用pandas的函数来处理
            all_actors_series = all_data['录音师'][pd.notna(all_data['录音师'])]
            all_actors = pd.Series(all_actors_series).unique().tolist()
            success_actors = voice_actor_status["success"]
            # 无数据的录音师 = 所有录音师 - 成功读取的录音师
            no_data_actors = set(all_actors) - success_actors
            # 过滤掉空值
            no_data_actors = {actor for actor in no_data_actors if pd.notna(actor) and actor != ''}
            voice_actor_status["no_data"] = no_data_actors
            
            # 从错误文件中提取失败的录音师
            for filename, error in error_files:
                # 尝试从文件名中提取录音师信息（如果文件名包含录音师名称）
                # 这里可以根据实际文件命名规则进行调整
                pass
        
        # 创建和保存结算汇总表
        summary_df = create_settlement_summary(all_data)
        
        # 在结算汇总表中添加税后列，并计算个税和税前金额
        # 税后列就是小计(元)列的副本
        summary_df['税后'] = summary_df['小计(元)']
        
        # 计算个税和税前列
        tax_info_list = []
        for _, row in summary_df.iterrows():
            tax, before_tax = calculate_tax_info(row['小计(元)'])
            tax_info_list.append((tax, before_tax))
        
        # 添加个税和税前列
        summary_df['个税'] = [tax for tax, _ in tax_info_list]
        summary_df['税前'] = [before_tax for _, before_tax in tax_info_list]
        
        # 重新排列列顺序，使税后、个税、税前列紧跟在小计(元)之后
        column_order = [
            '录音师', '整套', '新增', '全新单价', '补录单价', '小计(元)', 
            '税后', '个税', '税前'  # 保持正确的列顺序
        ]
        summary_df = summary_df[column_order]
        
        # 创建终表
        final_df = create_final_table(summary_df)
        
        # 生成结果文件
        output_filename = f"录音师薪资结算结果_{int(time.time())}.xlsx"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        # 保存文件（包含主表、结算汇总表和终表）
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 保存主表
            all_data.to_excel(writer, sheet_name='主表', index=False)
            
            # 保存结算汇总表
            summary_df.to_excel(writer, sheet_name='结算汇总', index=False)
            
            # 保存终表
            final_df.to_excel(writer, sheet_name='终表', index=False)
        
        # 保存文件路径到全局变量，供下载使用
        app.config['OUTPUT_FILE_PATH'] = output_path
        app.config['OUTPUT_FILE_NAME'] = output_filename
        
        # 构建成功消息，包含详细的处理信息
        success_msg = f"处理完成！成功处理 {len(processed_files)} 个文件"
        if error_files:
            success_msg += f"，{len(error_files)} 个文件处理失败"
        
        # 输出数据统计
        total_records = len(all_data)
        non_empty_records = len(all_data.dropna(how='all'))
        
        # 检查关键列的数据质量
        key_columns = ['日期', '需求人', '项目名称', '录音师']
        data_quality_info = ""
        for col in key_columns:
            if col in all_data.columns:
                # 统计非空值
                non_empty = (~pd.isna(all_data[col])).sum()
                data_quality_info += f"{col}非空值: {non_empty}/{total_records}\n"
        
        # 准备录音师状态信息
        voice_actor_info = {
            "success": sorted(list(voice_actor_status["success"])),
            "failed": sorted(list(voice_actor_status["failed"])),
            "no_data": sorted(list(voice_actor_status["no_data"]))
        }
        
        # 准备错误详情信息
        error_info_detail = {
            "read_error_count": len(error_details["read_error"]),
            "no_data_count": len(error_details["no_data"]),
            "other_error_count": len(error_details["other_error"]),
            "read_error_files": [filename for filename, _ in error_details["read_error"]],
            "no_data_files": [filename for filename, _ in error_details["no_data"]],
            "other_error_files": [filename for filename, _ in error_details["other_error"]]
        }
        
        return jsonify({
            'success': True,
            'message': success_msg,
            'output_path': output_path,
            'filename': output_filename,
            'statistics': {
                'total_records': total_records,
                'non_empty_records': non_empty_records,
                'data_quality': data_quality_info
            },
            'voice_actor_status': voice_actor_info,  # 添加录音师状态信息
            'error_details': error_info_detail  # 添加错误详情信息
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'处理过程中出错: {str(e)}'})

@app.route('/read_excel_info', methods=['POST'])
def read_excel_info():
    try:
        # 获取上传的文件
        file = request.files.get('file')
        
        if not file:
            return jsonify({'success': False, 'error': '请上传文件'})
        
        # 检查文件类型
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': '请上传Excel文件 (.xlsx 或 .xls)'})
        
        # 保存文件到临时位置
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)
        
        # 读取Excel文件的工作表列表
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        # 读取第一个工作表的列名
        columns = []
        if sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_names[0], nrows=1)
                columns = list(df.columns) if not df.empty else []
            except Exception:
                # 如果读取第一个工作表失败，尝试其他工作表
                for sheet in sheet_names:
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet, nrows=1)
                        columns = list(df.columns) if not df.empty else []
                        break
                    except Exception:
                        continue
        
        return jsonify({
            'success': True,
            'sheets': sheet_names,
            'columns': columns
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'读取文件信息出错: {str(e)}'})


@app.route('/read_sheet_columns', methods=['POST'])
def read_sheet_columns():
    try:
        # 获取上传的文件和工作表名称
        file = request.files.get('file')
        sheet_name = request.form.get('sheet_name')
        
        if not file:
            return jsonify({'success': False, 'error': '请上传文件'})
        
        if not sheet_name:
            return jsonify({'success': False, 'error': '请提供工作表名称'})
        
        # 检查文件类型
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': '请上传Excel文件 (.xlsx 或 .xls)'})
        
        # 保存文件到临时位置
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)
        
        # 读取指定工作表的列名
        df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=1)
        columns = list(df.columns) if not df.empty else []
        
        return jsonify({
            'success': True,
            'columns': columns
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'读取工作表列信息出错: {str(e)}'})


@app.route('/auto_detect_node_columns', methods=['POST'])
def auto_detect_node_columns():
    try:
        # 获取上传的文件和工作表名称
        file = request.files.get('file')
        sheet_name = request.form.get('sheet_name')
        
        if not file:
            return jsonify({'success': False, 'error': '请上传文件'})
        
        if not sheet_name:
            return jsonify({'success': False, 'error': '请提供工作表名称'})
        
        # 检查文件类型
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': '请上传Excel文件 (.xlsx 或 .xls)'})
        
        # 保存文件到临时位置
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)
        
        # 读取指定工作表的数据
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # 自动识别节点话术列（格式：节点话术X）
        node_columns = []
        if not df.empty:
            col_names = [str(col).strip() for col in df.columns.tolist()]
            import re
            node_col_pattern = re.compile(r'^\s*节点话术\s*(\d+)\s*$')
            
            for col in col_names:
                match = node_col_pattern.match(col)
                if match:
                    try:
                        col_num = int(match.group(1))
                        if col_num > 0:
                            node_columns.append(col)
                    except ValueError:
                        continue
            
            # 按数字排序
            def extract_number(col_name):
                match = re.search(r'\d+', col_name)
                return int(match.group()) if match else 0
            node_columns.sort(key=extract_number)
        
        return jsonify({
            'success': True,
            'node_columns': node_columns
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'自动识别节点话术列出错: {str(e)}'})


@app.route('/comparison_process', methods=['POST'])
def comparison_process():
    try:
        # 获取上传的文件
        standard_file = request.files.get('standard_file')
        matching_file = request.files.get('matching_file')
        standard_sheet = request.form.get('standard_sheet')
        matching_sheet = request.form.get('matching_sheet')
        selected_std_cols = request.form.getlist('selected_std_cols')
        selected_match_cols = request.form.getlist('selected_match_cols')
        
        if not standard_file or not matching_file:
            return jsonify({'success': False, 'error': '请上传两个Excel文件'})
        
        # 检查文件类型
        if not standard_file.filename or not standard_file.filename.endswith(('.xlsx', '.xls')) or not matching_file.filename or not matching_file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': '请上传Excel文件 (.xlsx 或 .xls)'})
        
        # 保存文件到临时位置
        temp_dir = tempfile.mkdtemp()
        if not standard_file.filename or not matching_file.filename:
            return jsonify({'success': False, 'error': '文件名无效'})
        standard_path = os.path.join(temp_dir, standard_file.filename)
        matching_path = os.path.join(temp_dir, matching_file.filename)
        standard_file.save(standard_path)
        matching_file.save(matching_path)
        
        # 读取Excel文件
        df_standard = pd.read_excel(standard_path, sheet_name=standard_sheet)
        df_matching = pd.read_excel(matching_path, sheet_name=matching_sheet)
        
        # 确保df_standard和df_matching是DataFrame类型
        if not isinstance(df_standard, pd.DataFrame):
            return jsonify({'success': False, 'error': '无法读取标准表数据'})
        if not isinstance(df_matching, pd.DataFrame):
            return jsonify({'success': False, 'error': '无法读取待匹配表数据'})
        
        # 实现话术比对逻辑
        # 标准表需要选择列，待匹配表自动识别节点话术列
        
        # 验证必要列
        required_col = "意图名称"
        if required_col not in df_standard.columns:
            return jsonify({'success': False, 'error': f'标准表缺少必要列: \'{required_col}\''})
        if required_col not in df_matching.columns:
            return jsonify({'success': False, 'error': f'待匹配表缺少必要列: \'{required_col}\''})
        
        if not selected_std_cols:
            return jsonify({'success': False, 'error': '请至少选择一个标准表话术列'})
        
        if not selected_match_cols:
            return jsonify({'success': False, 'error': '请至少选择一个待匹配表话术列'})
        
        # 处理标准表
        std_data = df_standard.copy()
        
        # 合并标准表选中的列（保留原始内容用于显示）
        def clean_text_for_comparison(text):
            if pd.isna(text):
                return ""
            text_str = str(text).strip()
            # 移除空白字符
            import re
            text_str = re.sub(r'\s+', '', text_str, flags=re.UNICODE)
            # 移除零宽字符
            text_str = re.sub(r'[\u200B-\u200D\uFEFF]', '', text_str)
            # 移除标点符号（保留中文、英文、数字）仅用于比对
            text_str = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text_str)
            return text_str
        
        # 合并标准表选中的列（保留原始内容）
        def combine_std_columns_with_original(row):
            return ''.join([str(row[col]) if not pd.isna(row[col]) else "" for col in selected_std_cols])
        
        std_data["原始标准话术"] = std_data.apply(combine_std_columns_with_original, axis=1)
        std_data["合并后标准话术"] = std_data.apply(lambda row: ''.join([clean_text_for_comparison(row[col]) for col in selected_std_cols if not pd.isna(row[col]) and clean_text_for_comparison(row[col]) != ""]), axis=1)
        
        # 清理意图名称
        std_data[required_col] = std_data[required_col].astype(str).str.strip()
        std_data = std_data.drop_duplicates(subset=[required_col], keep="first")
        
        # 过滤无效意图
        std_data = std_data[
            (std_data[required_col].notna()) &
            (std_data[required_col] != "") &
            (std_data["合并后标准话术"] != "")
        ]
        
        if len(std_data) == 0:
            return jsonify({'success': False, 'error': '标准表无有效意图数据'})
        
        # 处理待匹配表
        match_data = df_matching.copy()
        match_data[required_col] = match_data[required_col].astype(str).str.strip()
        match_data = match_data.drop_duplicates(subset=[required_col], keep="first")
        
        # 过滤无效意图
        match_data = match_data[
            (match_data[required_col].notna()) &
            (match_data[required_col] != "")
        ]
        
        # 合并待匹配表选中的列（保留原始内容）
        if selected_match_cols:
            def combine_columns_with_original(row):
                return ''.join([str(row[col]) if not pd.isna(row[col]) else "" for col in selected_match_cols])
            
            def combine_columns_for_comparison(row):
                return ''.join([clean_text_for_comparison(row[col]) for col in selected_match_cols if not pd.isna(row[col]) and clean_text_for_comparison(row[col]) != ""])
            
            match_data["原始待匹配话术"] = match_data.apply(combine_columns_with_original, axis=1)
            match_data["合并后待匹配话术"] = match_data.apply(combine_columns_for_comparison, axis=1)
        else:
            match_data["原始待匹配话术"] = ""
            match_data["合并后待匹配话术"] = ""
        
        # 建立意图映射
        std_intents = set(std_data[required_col].tolist())
        match_intents = set(match_data[required_col].tolist())
        matched_intents = std_intents & match_intents
        unmatched_intents = std_intents - match_intents  # 标准表有但待匹配表没有
        extra_intents = match_intents - std_intents      # 标准表没有但待匹配表有
        
        # 执行比对
        result_data = []
        # 动态意图-话术映射
        intent_to_script = {}
        intent_to_original_script = {}  # 用于存储原始话术
        for idx, row in match_data.iterrows():
            intent_to_script[row[required_col]] = row["合并后待匹配话术"]
            intent_to_original_script[row[required_col]] = row["原始待匹配话术"]
        
        # 遍历标准表意图进行比对
        for idx, row in std_data.iterrows():
            intent_name = row[required_col]
            std_script = row["合并后标准话术"]
            std_original_script = row["原始标准话术"]
            match_script = intent_to_script.get(intent_name, "")
            match_original_script = intent_to_original_script.get(intent_name, "")
            
            # 执行比对（使用清理后的文本进行比对）
            std_clean = clean_text_for_comparison(std_script)
            match_clean = clean_text_for_comparison(match_script)
            
            if std_clean == match_clean:
                comparison = "相同"
                diff_note = ""
            else:
                comparison = "不同"
                # 使用详细比较函数，传入清理后的文本用于比较
                diff_note = compare_texts_detailed(std_script, match_script)
                if not diff_note:
                    diff_note = "话术内容不一致"
            
            # 构建结果条目（使用原始话术内容显示）
            result_entry = {
                "意图名称": intent_name,
                "匹配结论": comparison,
                "标准表话术": std_original_script,
                "待匹配表话术": match_original_script,
                "差异说明": diff_note
            }
            result_data.append(result_entry)
        
        # 处理标准表有但待匹配表没有的意图
        for intent_name in unmatched_intents:
            # 查找标准表中的原始话术
            std_original = ""
            std_rows = std_data[std_data[required_col] == intent_name]
            if len(std_rows) > 0:
                try:
                    # 使用values获取值
                    std_original = str(list(std_rows["原始标准话术"])[0]) if len(list(std_rows["原始标准话术"])) > 0 else ""
                    # 检查是否为NaN
                    if isinstance(std_original, float) and pd.isna(std_original):
                        std_original = ""
                except:
                    std_original = "[无法获取标准表话术内容]"
            
            result_entry = {
                "意图名称": intent_name,
                "匹配结论": "未匹配",
                "标准表话术": std_original,
                "待匹配表话术": "",
                "差异说明": "待匹配表中未找到该意图"
            }
            result_data.append(result_entry)
        
        # 处理标准表没有但待匹配表有的意图
        for intent_name in extra_intents:
            # 查找待匹配表中的原始话术
            match_original = ""
            match_rows = match_data[match_data[required_col] == intent_name]
            if len(match_rows) > 0:
                try:
                    # 使用values获取值
                    match_original = str(list(match_rows["原始待匹配话术"])[0]) if len(list(match_rows["原始待匹配话术"])) > 0 else ""
                    # 检查是否为NaN
                    if isinstance(match_original, float) and pd.isna(match_original):
                        match_original = ""
                except:
                    match_original = "[无法获取待匹配表话术内容]"
            
            result_entry = {
                "意图名称": intent_name,
                "匹配结论": "多余",
                "标准表话术": "",
                "待匹配表话术": match_original,
                "差异说明": "标准表中未找到该意图"
            }
            result_data.append(result_entry)
        
        # 生成结果DataFrame
        result_df = pd.DataFrame(result_data)
        match_count = sum(1 for val in result_df["匹配结论"] if val == "相同")
        mismatch_count = sum(1 for val in result_df["匹配结论"] if val == "不同")
        error_count = 0  # 这里没有处理错误的情况
        unmatched_count = sum(1 for val in result_df["匹配结论"] if val == "未匹配")
        extra_count = sum(1 for val in result_df["匹配结论"] if val == "多余")
        
        # 生成结果文件
        output_filename = f"话术比对结果_{int(time.time())}.xlsx"
        output_path = os.path.join(temp_dir, output_filename)
        
        # 保存完整的结果数据到Excel文件
        result_df.to_excel(output_path, index=False)
        
        # 保存文件路径供下载使用
        app.config['OUTPUT_FILE_PATH'] = output_path
        app.config['OUTPUT_FILE_NAME'] = output_filename
        
        return jsonify({
            'success': True,
            'message': '比对完成',
            'match_count': match_count,
            'mismatch_count': mismatch_count,
            'error_count': error_count,
            'unmatched_count': unmatched_count,
            'extra_count': extra_count,
            'filename': output_filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'处理过程中出错: {str(e)}'})

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Log the error
    app.logger.error(f'Unhandled exception: {str(e)}', exc_info=True)
    # Return JSON error for API routes
    return jsonify({'success': False, 'error': '服务器内部错误，请稍后重试'}), 500

@app.route('/health')
def health_check():
    """健康检查路由，用于验证应用是否正常运行"""
    return jsonify({'status': 'ok', 'message': '应用运行正常'}), 200

@app.route('/test')
def test():
    """测试路由，用于验证应用是否正常工作"""
    return '<h1>测试成功</h1><p>应用路由工作正常</p>'

@app.route('/download/<filename>')
def download_file(filename):
    try:
        if app.config.get('OUTPUT_FILE_PATH') and app.config.get('OUTPUT_FILE_NAME') == filename:
            return send_file(app.config['OUTPUT_FILE_PATH'], as_attachment=True)
        else:
            return "文件未找到", 404
    except Exception as e:
        return f"下载出错: {str(e)}", 500

# 确保在PythonAnywhere环境中不启动内置服务器
if __name__ == '__main__':
    # 检查是否在PythonAnywhere环境中运行
    if 'PYTHONANYWHERE_DOMAIN' in os.environ:
        # PythonAnywhere环境
        print("[部署] 检测到PythonAnywhere环境")
        # 在PythonAnywhere中不需要调用app.run()，由uWSGI处理
        pass
    else:
        # 本地开发环境
        print("[开发] 本地开发环境")
        app.run(host='127.0.0.1', port=5000, debug=True)