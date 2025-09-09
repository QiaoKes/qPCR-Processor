"""
数据读取模块
负责从Excel文件中读取实验数据
"""
import pandas as pd
import os
from typing import List, Dict, Any
import logging

class DataReader:
    """数据读取器类"""
    
    def __init__(self, source_dir: str):
        """
        初始化数据读取器
        
        Args:
            source_dir (str): 源数据目录路径
        """
        self.source_dir = source_dir
        self.logger = logging.getLogger(__name__)
    
    def get_file_list(self) -> List[str]:
        """
        获取源目录中的所有xls文件
        
        Returns:
            List[str]: 文件路径列表
        """
        try:
            files = []
            for file in os.listdir(self.source_dir):
                if file.endswith('.xls') or file.endswith('.xlsx'):
                    files.append(os.path.join(self.source_dir, file))
            return files
        except Exception as e:
            self.logger.error(f"获取文件列表失败: {e}")
            return []
    
    def extract_file_prefix(self, file_path: str) -> str:
        """
        从文件名中提取前缀（第一个空格前的部分）
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            str: 文件前缀
        """
        filename = os.path.basename(file_path)
        return filename.split(' ')[0] if ' ' in filename else filename.split('.')[0]
    
    def read_excel_data(self, file_path: str) -> pd.DataFrame:
        """
        读取Excel文件中的Results sheet
        
        Args:
            file_path (str): Excel文件路径
            
        Returns:
            pd.DataFrame: 读取的数据
        """
        try:
            # 读取Results sheet
            df = pd.read_excel(file_path, sheet_name='Results')
            self.logger.info(f"成功读取文件: {file_path}, 数据行数: {len(df)}")
            return df
        except Exception as e:
            self.logger.error(f"读取文件失败 {file_path}: {e}")
            return pd.DataFrame()
    
    def extract_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        提取需要的列
        
        Args:
            df (pd.DataFrame): 原始数据
            
        Returns:
            pd.DataFrame: 提取后的数据
        """
        required_columns = ['Experiment Name', 'Well Position', 'Target Name', 'Sample Name', 'CT']
        
        # 检查所需列是否存在
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.logger.warning(f"缺少列: {missing_columns}")
            # 创建缺少的列并填充空值
            for col in missing_columns:
                df[col] = None
        
        return df[required_columns].copy()
