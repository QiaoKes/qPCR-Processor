"""
数据处理模块
负责对实验数据进行各种计算和处理
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
import json

class DataProcessor:
    """数据处理器类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化数据处理器
        
        Args:
            config_path (str): 配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.sample_mapping = {}
        self.reference_genes = ['GAPDH', 'TBP']  # 默认参考基因
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """
        加载配置文件
        
        Args:
            config_path (str): 配置文件路径
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.sample_mapping = config.get('sample_mapping', {})
                self.reference_genes = config.get('reference_genes', ['GAPDH', 'TBP'])
            self.logger.info(f"配置文件加载成功: {config_path}")
            self.logger.info(f"参考基因设置为: {self.reference_genes}")
        except Exception as e:
            self.logger.warning(f"配置文件加载失败: {e}")
    
    def set_reference_genes(self, reference_genes: List[str]):
        """
        设置参考基因列表
        
        Args:
            reference_genes (List[str]): 参考基因名称列表
        """
        self.reference_genes = reference_genes
        self.logger.info(f"参考基因设置为: {self.reference_genes}")
    
    def get_reference_genes(self) -> List[str]:
        """
        获取当前配置的参考基因列表
        
        Returns:
            List[str]: 参考基因名称列表
        """
        return self.reference_genes.copy()
    
    def apply_sample_mapping(self, df: pd.DataFrame, file_prefix: Optional[str] = None) -> pd.DataFrame:
        """
        应用样本名称映射，支持按文件前缀分组的映射
        
        Args:
            df (pd.DataFrame): 原始数据
            file_prefix (str): 文件前缀，用于确定使用哪个映射组
            
        Returns:
            pd.DataFrame: 映射后的数据
        """
        df = df.copy()
        
        # 确保有Experiment Name列
        if 'Experiment Name' not in df.columns:
            df['Experiment Name'] = df['Sample Name']
        
        if self.sample_mapping and file_prefix:
            # 处理嵌套结构的映射
            if file_prefix in self.sample_mapping:
                mapping_dict = self.sample_mapping[file_prefix]
                self.logger.info(f"使用文件 {file_prefix} 的专用映射")
                
                # 创建一个能处理数字和字符串的映射函数
                def safe_map(sample_name):
                    # 先尝试直接映射
                    if sample_name in mapping_dict:
                        return mapping_dict[sample_name]
                    # 尝试转换为字符串后映射
                    str_sample = str(sample_name)
                    if str_sample in mapping_dict:
                        return mapping_dict[str_sample]
                    # 如果是字符串，尝试转换为数字后再转回字符串映射
                    try:
                        if isinstance(sample_name, str):
                            num_sample = str(int(float(sample_name)))
                            if num_sample in mapping_dict:
                                return mapping_dict[num_sample]
                    except (ValueError, TypeError):
                        pass
                    return sample_name
                
                # 应用映射
                df['Experiment Name'] = df['Sample Name'].apply(safe_map)
                
                # 统计成功映射的数量
                mapped_count = (df['Experiment Name'] != df['Sample Name']).sum()
                self.logger.info(f"文件 {file_prefix}: 应用了样本映射，映射了{mapped_count}个样本")
                
                # 显示一些映射示例用于调试
                unique_samples = df['Sample Name'].unique()[:5]  # 只显示前5个
                for sample in unique_samples:
                    mapped = safe_map(sample)
                    if mapped != sample:
                        self.logger.info(f"文件 {file_prefix} 映射示例: '{sample}' -> '{mapped}'")
            else:
                self.logger.warning(f"未找到文件 {file_prefix} 的映射配置，保持原Sample Name作为Experiment Name")
        else:
            self.logger.warning("没有提供文件前缀或映射配置为空，保持原Sample Name作为Experiment Name")
            
        return df
    
    def process_ct_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理CT值的特殊逻辑
        
        Args:
            df (pd.DataFrame): 原始数据
            
        Returns:
            pd.DataFrame: 处理后的数据
        """
        df = df.copy()
        
        # 按Sample Name分组，然后在每个组内按Target Name处理
        grouped_by_sample = df.groupby('Sample Name')
        
        for sample_name, sample_group in grouped_by_sample:
            # 在当前Sample Name组内，按Target Name分组
            target_grouped = sample_group.groupby('Target Name')
            
            for target_name, target_group in target_grouped:
                # 获取当前分组的索引
                group_indices = target_group.index
                
                # 检查CT值，将'Undetermined'转换为NaN进行处理
                ct_values = pd.to_numeric(target_group['CT'], errors='coerce')
                
                # 如果所有值都是Undetermined（即NaN）
                if ct_values.isna().all():
                    df.loc[group_indices, 'CT'] = 0
                    self.logger.info(f"样本 {sample_name} 的 {target_name} 基因所有CT值为Undetermined，设置为0")
                else:
                    # 如果有非Undetermined值，计算平均值
                    mean_value = ct_values.mean()
                    # 将Undetermined值替换为平均值
                    mask = target_group['CT'] == 'Undetermined'
                    df.loc[group_indices[mask], 'CT'] = mean_value
                    self.logger.info(f"样本 {sample_name} 的 {target_name} 基因Undetermined值替换为平均值: {mean_value:.6f}")
        
        return df
    
    def calculate_extended_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算扩展指标，如果CT值为0，则后续扩展指标全部设置为0
        
        Args:
            df (pd.DataFrame): 处理后的基础数据
            
        Returns:
            pd.DataFrame: 包含所有计算指标的数据
        """
        # 确保CT列为数值类型
        df['CT'] = pd.to_numeric(df['CT'], errors='coerce')
        
        # 自定义排序：参考基因放在每个Sample Name分组的前面
        def custom_sort_key(row):
            sample_name = str(row['Sample Name'])
            target_name = str(row['Target Name'])
            
            # 为参考基因分配较小的排序值，使其排在前面
            if target_name in self.reference_genes:
                ref_priority = str(self.reference_genes.index(target_name))
                return (sample_name, '0', ref_priority)  # 参考基因优先级为0
            else:
                return (sample_name, '1', target_name)  # 其他基因优先级为1
        
        # 按自定义排序规则排序
        df_sorted = df.copy()
        df_sorted['sort_key'] = df_sorted.apply(custom_sort_key, axis=1)
        df_sorted = df_sorted.sort_values('sort_key').drop('sort_key', axis=1).reset_index(drop=True)
        
        # 按Sample Name和Target Name分组计算Ct Mean
        # 特殊处理：如果组内有CT值为0的数据，则该组的Ct Mean也应该为0
        ct_mean_stats = {}
        for (sample_name, target_name), group in df_sorted.groupby(['Sample Name', 'Target Name']):
            group_ct_values = group['CT']
            
            # 检查组内是否有CT值为0的数据
            if (group_ct_values == 0).any():
                # 如果组内有CT值为0，则该组的Ct Mean设为0
                ct_mean_stats[(sample_name, target_name)] = 0
            else:
                # 如果组内没有CT值为0，则正常计算平均值
                ct_mean_stats[(sample_name, target_name)] = group_ct_values.mean()
        
        # 创建结果数据框并添加Ct Mean
        result_df = df_sorted.copy()
        result_df['Ct Mean'] = result_df.apply(
            lambda row: ct_mean_stats.get((row['Sample Name'], row['Target Name']), np.nan),
            axis=1
        )
        
        # 为每个参考基因计算指标
        for i, reference_gene in enumerate(self.reference_genes):
            # 在第一个参考基因前添加空白列
            if i == 0:
                result_df[''] = ''
            
            # 计算当前参考基因的指标
            result_df = self._calculate_reference_gene_metrics(result_df, reference_gene)
            
            # 在参考基因间添加空白列（除了最后一个）
            if i < len(self.reference_genes) - 1:
                result_df[f' '] = ''  # 使用空格避免重复列名
        
        return result_df
    
    def _calculate_reference_gene_metrics(self, df: pd.DataFrame, reference_gene: str) -> pd.DataFrame:
        """
        计算参考基因相关指标，如果CT值为0，则该行的指标设置为0
        
        Args:
            df (pd.DataFrame): 数据框
            reference_gene (str): 参考基因名称（GAPDH或TBP）
            
        Returns:
            pd.DataFrame: 添加了计算指标的数据框
        """
        df = df.copy()
        
        # 计算参考基因的Cq mean - 为每个样本获取参考基因的Cq mean值
        ref_cq_col = f'{reference_gene} Cq mean'
        
        # 先创建一个映射字典，保存每个样本的参考基因Cq mean值
        sample_ref_cq_map = {}
        for sample_name in df['Sample Name'].unique():
            sample_data = df[df['Sample Name'] == sample_name]
            ref_data = sample_data[sample_data['Target Name'] == reference_gene]
            if not ref_data.empty:
                sample_ref_cq_map[sample_name] = ref_data['Ct Mean'].iloc[0]
        
        # 为所有行添加参考基因Cq mean列
        df[ref_cq_col] = df['Sample Name'].map(sample_ref_cq_map)
        
        # 计算ΔCT：当前行的CT值 - 参考基因Cq mean
        delta_ct_col = f'{reference_gene} ΔCT'
        df[delta_ct_col] = df['CT'] - df[ref_cq_col]
        
        # 计算2^(-ΔCT)
        two_power_col = f'{reference_gene} 2^(-ΔCT)'
        df[two_power_col] = 2 ** (-df[delta_ct_col])
        
        # 按Sample Name和Target Name分组计算Average和Stdv
        average_col = f'{reference_gene} Average'
        stdv_col = f'{reference_gene} Stdv'
        
        # 对每个(Sample Name, Target Name)组合计算统计量
        # 需要特殊处理：如果组内有CT值为0的数据，则该组的Average和Stdv都应该为0
        group_stats = {}
        for (sample_name, target_name), group in df.groupby(['Sample Name', 'Target Name']):
            group_ct_values = group['CT']
            group_two_power_values = group[two_power_col]
            
            # 检查组内是否有CT值为0的数据
            if (group_ct_values == 0).any():
                # 如果组内有CT值为0，则该组的Average和Stdv都设为0
                group_stats[(sample_name, target_name)] = {'avg': 0, 'std': 0}
            else:
                # 如果组内没有CT值为0，则正常计算
                group_stats[(sample_name, target_name)] = {
                    'avg': group_two_power_values.mean(),
                    'std': group_two_power_values.std()
                }
        
        # 将统计量映射回原数据
        df[average_col] = df.apply(
            lambda row: group_stats.get((row['Sample Name'], row['Target Name']), {}).get('avg', np.nan),
            axis=1
        )
        df[stdv_col] = df.apply(
            lambda row: group_stats.get((row['Sample Name'], row['Target Name']), {}).get('std', np.nan),
            axis=1
        )
        
        # 对于单个CT值为0的行，确保其个体指标也为0
        ct_zero_mask = (df['CT'] == 0)
        df.loc[ct_zero_mask, ref_cq_col] = 0
        df.loc[ct_zero_mask, delta_ct_col] = 0
        df.loc[ct_zero_mask, two_power_col] = 0
        
        return df
