"""
数据写入模块
负责将处理后的数据写入Excel文件
"""
import pandas as pd
import os
from typing import Dict, List, Optional
import logging
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.error_bar import ErrorBars
import json

class DataWriter:
    """数据写入器类"""
    
    def __init__(self, output_dir: str, config_path: Optional[str] = None):
        """
        初始化数据写入器
        
        Args:
            output_dir (str): 输出目录路径
            config_path (str): 配置文件路径
        """
        self.output_dir = output_dir
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.reference_genes = ['GAPDH', 'TBP']  # 默认参考基因
        self.target_gene_order = []  # 默认目标基因顺序数组（空数组表示按字母排序）
        self.error_threshold = 0.3  # 默认误差告警阈值
        
        # 加载配置文件获取参考基因和图表布局
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.reference_genes = config.get('reference_genes', self.reference_genes)
                    self.target_gene_order = config.get('target_gene_order', self.target_gene_order)
                    self.error_threshold = config.get('error_threshold', self.error_threshold)
                    self.chart_layout = config.get('chart_layout', {})
            except Exception as e:
                self.logger.warning(f"无法加载配置文件中的参考基因设置: {e}")
        else:
            self.chart_layout = {}
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
    
    def write_to_excel(self, data_dict: Dict[str, pd.DataFrame], output_filename: str = 'processed_data.xlsx'):
        """
        将数据字典写入Excel文件的不同sheet中
        
        Args:
            data_dict (Dict[str, pd.DataFrame]): 数据字典，key为sheet名称，value为数据框
            output_filename (str): 输出文件名
        """
        output_path = os.path.join(self.output_dir, output_filename)
        
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 首先写入原始处理数据
                for sheet_name, df in data_dict.items():
                    # 确保sheet名称符合Excel要求
                    safe_sheet_name = self._sanitize_sheet_name(sheet_name)
                    
                    # 统一处理数值精度：保留7位小数
                    df_formatted = self._format_numeric_precision(df)
                    
                    df_formatted.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                    self.logger.info(f"数据已写入sheet: {safe_sheet_name}, 行数: {len(df)}")
                
                # 为每个原始sheet生成对应的参考基因相关sheet
                for sheet_name, df in data_dict.items():
                    self._generate_reference_gene_sheets(writer, sheet_name, df)
                
                # 生成合并的参考基因sheet（Merge(GAPDH), Merge(TBP)等）
                self._generate_merged_reference_gene_sheets(writer, data_dict)
            
            self.logger.info(f"数据成功保存到: {output_path}")
            
            # 单独处理图表，因为pandas ExcelWriter不支持图表
            self._add_charts_to_excel(output_path, data_dict)
            
            return output_path
        
        except Exception as e:
            self.logger.error(f"写入Excel文件失败: {e}")
            return None
    
    def _sanitize_sheet_name(self, name: str) -> str:
        """
        清理sheet名称，确保符合Excel要求
        
        Args:
            name (str): 原始名称
            
        Returns:
            str: 清理后的名称
        """
        # Excel sheet名称不能包含这些字符：\ / ? * [ ]
        invalid_chars = ['\\', '/', '?', '*', '[', ']', ':']
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # 限制长度（Excel sheet名称最大31个字符）
        if len(name) > 31:
            name = name[:31]
        
        return name
    
    def _format_numeric_precision(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        统一处理数值列的精度，保留7位有效数字，确保Excel兼容性
        使用pandas内置的格式化功能
        
        Args:
            df (pd.DataFrame): 原始数据框
            
        Returns:
            pd.DataFrame: 格式化后的数据框
        """
        df_formatted = df.copy()
        
        def smart_format(x):
            """智能格式化：7位有效数字，保持数值类型以确保Excel兼容性"""
            if pd.isna(x) or x == 0:
                return x
                
            import numpy as np
            abs_x = abs(x)
            
            # 对于极小或极大的数，仍然返回数值类型，让Excel自动处理科学计数法显示
            if abs_x < 1e-4 or abs_x >= 1e6:
                # 保持浮点数格式，Excel会自动使用科学计数法显示
                # 使用numpy的格式化保持精度，但返回浮点数
                if abs_x < 1e-15:  # 极小数值，避免精度丢失
                    return float(f"{x:.5e}")
                else:
                    # 对于可以精确表示的数值，直接保留有效数字
                    significant_digits = 7
                    order_of_magnitude = int(np.floor(np.log10(abs_x)))
                    scale = 10 ** (significant_digits - 1 - order_of_magnitude)
                    return round(x * scale) / scale
            else:
                # 使用pandas的精度控制，保持浮点数类型
                # 计算所需小数位数以保持7位有效数字
                if abs_x >= 1:
                    integer_digits = len(str(int(abs_x)))
                    decimal_places = max(0, 7 - integer_digits)
                else:
                    # 对于小数，找到第一个有效数字位置
                    decimal_places = -int(np.floor(np.log10(abs_x))) + 6
                
                # 限制小数位数，避免过长
                decimal_places = min(decimal_places, 10)
                return round(x, decimal_places)
        
        # 使用pandas的apply方法处理数值列
        for col in df_formatted.columns:
            if pd.api.types.is_numeric_dtype(df_formatted[col]):
                # 直接对数值列应用格式化，保持数值类型
                df_formatted[col] = df_formatted[col].apply(smart_format)
            else:
                # 对于非数值列，尝试转换后格式化
                try:
                    # 使用pandas的to_numeric进行转换
                    numeric_series = pd.to_numeric(df_formatted[col], errors='coerce')
                    if not numeric_series.isna().all():
                        # 只对能转换为数值的元素进行格式化，保持数值类型
                        mask = ~numeric_series.isna()
                        df_formatted.loc[mask, col] = numeric_series[mask].apply(smart_format)
                except:
                    # 转换失败保持原样
                    continue
        
        return df_formatted
    
    def save_individual_files(self, data_dict: Dict[str, pd.DataFrame]):
        """
        为每个数据集保存单独的Excel文件
        
        Args:
            data_dict (Dict[str, pd.DataFrame]): 数据字典
        """
        for name, df in data_dict.items():
            filename = f"{name}_processed.xlsx"
            output_path = os.path.join(self.output_dir, filename)
            
            try:
                # 统一处理数值精度：保留7位小数
                df_formatted = self._format_numeric_precision(df)
                df_formatted.to_excel(output_path, index=False)
                self.logger.info(f"单独文件保存成功: {output_path}")
            except Exception as e:
                self.logger.error(f"保存单独文件失败 {filename}: {e}")
    
    def _generate_reference_gene_sheets(self, writer, original_sheet_name: str, df: pd.DataFrame):
        """
        为每个参考基因生成对应的sheet页面
        
        Args:
            writer: Excel writer对象
            original_sheet_name (str): 原始sheet名称
            df (pd.DataFrame): 原始数据
        """
        for reference_gene in self.reference_genes:
            # 生成sheet名称，例如：P1(GAPDH), P1(TBP)
            ref_sheet_name = f"{original_sheet_name}({reference_gene})"
            safe_ref_sheet_name = self._sanitize_sheet_name(ref_sheet_name)
            
            # 生成参考基因相关的数据表格
            ref_data = self._create_reference_gene_data(df, reference_gene)
            
            if not ref_data.empty:
                ref_data.to_excel(writer, sheet_name=safe_ref_sheet_name, index=False)
                self.logger.info(f"生成参考基因sheet: {safe_ref_sheet_name}, 行数: {len(ref_data)}")
    
    def _generate_merged_reference_gene_sheets(self, writer, data_dict: Dict[str, pd.DataFrame]):
        """
        生成合并的参考基因sheet（如Merge(GAPDH), Merge(TBP)）
        将所有P1,P2,P3...数据中相同参考基因的内容合并到一个sheet中
        
        Args:
            writer: Excel writer对象
            data_dict (Dict[str, pd.DataFrame]): 原始数据字典
        """
        self.logger.info("开始生成合并的参考基因sheet...")
        
        for reference_gene in self.reference_genes:
            try:
                # 合并所有数据集中该参考基因的数据
                merged_data = self._merge_reference_gene_data(data_dict, reference_gene)
                
                if not merged_data.empty:
                    # 生成合并sheet名称，例如：Merge(GAPDH), Merge(TBP)
                    merged_sheet_name = f"Merge({reference_gene})"
                    safe_merged_sheet_name = self._sanitize_sheet_name(merged_sheet_name)
                    
                    # 写入合并的数据
                    merged_data.to_excel(writer, sheet_name=safe_merged_sheet_name, index=False)
                    self.logger.info(f"生成合并参考基因sheet: {safe_merged_sheet_name}, 行数: {len(merged_data)}")
                else:
                    self.logger.warning(f"参考基因 {reference_gene} 的合并数据为空，跳过生成合并sheet")
                    
            except Exception as e:
                self.logger.error(f"生成 {reference_gene} 合并sheet失败: {e}")
    
    def _merge_reference_gene_data(self, data_dict: Dict[str, pd.DataFrame], reference_gene: str) -> pd.DataFrame:
        """
        合并所有数据集中某个参考基因的数据
        按照原本的PX(GAPDH)逻辑调用原有方法，确保可靠性
        
        Args:
            data_dict (Dict[str, pd.DataFrame]): 原始数据字典
            reference_gene (str): 参考基因名称
            
        Returns:
            pd.DataFrame: 合并后的参考基因数据
        """
        # 收集所有数据集的参考基因相关数据
        all_ref_data_list = []
        
        for sheet_name, df in data_dict.items():
            # 为每个数据集生成参考基因数据（复用原有逻辑）
            ref_data = self._create_reference_gene_data(df, reference_gene)
            
            if not ref_data.empty:
                # 添加数据源标识列
                ref_data_with_source = ref_data.copy()
                ref_data_with_source['Data Source'] = sheet_name
                all_ref_data_list.append(ref_data_with_source)
                
                self.logger.info(f"从 {sheet_name} 提取了 {len(ref_data)} 行 {reference_gene} 数据")
        
        if not all_ref_data_list:
            self.logger.warning(f"没有找到任何 {reference_gene} 相关数据")
            return pd.DataFrame()
        
        # 合并所有数据
        merged_data = pd.concat(all_ref_data_list, ignore_index=True)
        
        # 重新排序：按照Target Name优先级，然后按Data Source，最后按Sample Name
        def merge_sort_key(row):
            target_name = row['Target Name']
            data_source = row['Data Source']
            
            target_priority = self._get_target_priority(target_name)
            
            # 数据源排序：P1, P2, P3...
            try:
                if data_source.startswith('P'):
                    source_num = int(data_source[1:]) if data_source[1:].isdigit() else 999
                else:
                    source_num = 1000 + hash(data_source) % 1000
            except (ValueError, IndexError):
                source_num = 1000
            
            # Sample Name排序
            try:
                sample_num = float(row['Sample Name']) if pd.notna(row['Sample Name']) else 999
                return (target_priority, target_name, source_num, data_source, sample_num)
            except (ValueError, TypeError):
                return (target_priority, target_name, source_num, data_source, str(row['Sample Name']) if pd.notna(row['Sample Name']) else 'zzz')
        
        merged_data['sort_key'] = merged_data.apply(merge_sort_key, axis=1)
        merged_data = merged_data.sort_values('sort_key').drop('sort_key', axis=1).reset_index(drop=True)
        
        # 记录合并后的统计信息
        target_counts = merged_data['Target Name'].value_counts()
        source_counts = merged_data['Data Source'].value_counts()
        
        self.logger.info(f"合并 {reference_gene} 数据完成: 总行数={len(merged_data)}")
        self.logger.info(f"Target Name分布: {dict(target_counts)}")
        self.logger.info(f"Data Source分布: {dict(source_counts)}")
        
        # 只在不同Target Name之间插入空白行，过滤掉来自不同数据源的重复空行
        rows_with_blanks = []
        warning_col = f'{reference_gene} Error Warning'
        
        # 保持已排序的Target Name顺序，不使用groupby（会重新排序）
        # 获取排序后的唯一Target Name列表，保持原有顺序
        unique_targets_ordered = []
        seen_targets = set()
        for _, row in merged_data.iterrows():
            target_name = row['Target Name']
            if target_name not in seen_targets:
                unique_targets_ordered.append(target_name)
                seen_targets.add(target_name)
        
        # 按照排序后的Target Name顺序处理数据
        for target_idx, target_name in enumerate(unique_targets_ordered):
            # 如果不是第一个Target，在前面插入6行空白行
            if target_idx > 0:
                for _n in range(6):
                    rows_with_blanks.append({
                        'Target Name': None,
                        'Sample Name': None,
                        'Experiment Name': None,
                        f'{reference_gene} Average': None,
                        f'{reference_gene} Stdv': None,
                        warning_col: None,
                        'Data Source': None
                    })
            
            # 添加该Target的所有数据行（来自不同数据源）
            target_rows = merged_data[merged_data['Target Name'] == target_name]
            for _, row in target_rows.iterrows():
                rows_with_blanks.append(row.to_dict())
        
        # 创建最终的合并数据框
        final_columns = ['Target Name', 'Sample Name', 'Experiment Name', 
                        f'{reference_gene} Average', f'{reference_gene} Stdv', 
                        warning_col, 'Data Source']
        result_df = pd.DataFrame(rows_with_blanks, columns=final_columns)
        
        # 格式化数值列
        result_df = self._format_numeric_precision(result_df)
        
        return result_df
    
    def _get_target_priority(self, target_name: str) -> int:
        """
        获取Target Name的排序优先级
        
        Args:
            target_name (str): 目标基因名称
            
        Returns:
            int: 排序优先级，数值越小优先级越高
        """
        # 为Target Name分配优先级
        if self.target_gene_order and len(self.target_gene_order) > 0:
            # 优先参考基因
            if target_name in self.reference_genes:
                try:
                    return self.reference_genes.index(target_name)
                except ValueError:
                    return 999

            # 如果配置了目标基因顺序数组且数组不为空
            if target_name in self.target_gene_order:
                # 在数组中的基因，按数组顺序排序
                return self.target_gene_order.index(target_name) + 100
            else:
                # 不在数组中的基因，按字母升序排序，排在数组基因之后
                # 使用首字母在字母表中的位置来排序
                first_char = target_name[0].upper() if target_name else 'Z'
                char_position = ord(first_char) - ord('A') if first_char.isalpha() else 26
                return len(self.target_gene_order) * 100 + char_position
        else:
            # 如果数组为空或未配置，参考基因在前，其他基因按字母顺序排列
            if target_name in self.reference_genes:
                try:
                    return self.reference_genes.index(target_name)
                except ValueError:
                    return 999
            else:
                # 非参考基因，优先级设置为比参考基因大的值，这样会排在参考基因之后
                # 使用首字母在字母表中的位置来排序
                first_char = target_name[0].upper() if target_name else 'Z'
                char_position = ord(first_char) - ord('A') if first_char.isalpha() else 26
                return len(self.reference_genes) * 100 + char_position
    
    def _check_error_warning(self, average_val, stdv_val) -> str:
        """
        检查误差是否超过阈值，返回告警信息
        
        Args:
            average_val: 平均值
            stdv_val: 标准差值
            
        Returns:
            str: 告警信息，如果超过阈值返回"误差过大"，否则返回空字符串
        """
        try:
            if pd.isna(average_val) or pd.isna(stdv_val) or average_val == 0:
                return ""
            
            # 计算相对误差：标准差/平均值
            relative_error = abs(stdv_val / average_val)
            
            # 如果相对误差超过阈值，返回告警
            if relative_error > self.error_threshold:
                return f"误差过大({relative_error:.1%})"
            else:
                return ""
        except (ZeroDivisionError, TypeError, ValueError):
            return ""
    
    def _create_reference_gene_data(self, df: pd.DataFrame, reference_gene: str) -> pd.DataFrame:
        """
        创建参考基因相关的数据表格
        
        Args:
            df (pd.DataFrame): 原始数据
            reference_gene (str): 参考基因名称
            
        Returns:
            pd.DataFrame: 参考基因相关的数据表格
        """
        # 需要的列：Target Name, Sample Name, Experiment Name, GAPDH/TBP Average, GAPDH/TBP Stdv
        average_col = f'{reference_gene} Average'
        stdv_col = f'{reference_gene} Stdv'
        
        # 检查这些列是否存在
        required_cols = ['Target Name', 'Sample Name', 'Experiment Name', average_col, stdv_col]
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            self.logger.warning(f"缺少列 {missing_cols}，跳过生成 {reference_gene} sheet")
            return pd.DataFrame()
        
        # 按Target Name和Sample Name分组，每个组取一行代表数据
        # 由于同组内的Average和Stdv值相同，取第一行即可
        grouped = df.groupby(['Target Name', 'Sample Name']).first().reset_index()
        
        # 选择需要的列并重命名
        base_df = grouped[['Target Name', 'Sample Name', 'Experiment Name', average_col, stdv_col]].copy()
        base_df.columns = ['Target Name', 'Sample Name', 'Experiment Name', f'{reference_gene} Average', f'{reference_gene} Stdv']

        # 添加误差告警列
        warning_col = f'{reference_gene} Error Warning'
        base_df[warning_col] = base_df.apply(
            lambda row: self._check_error_warning(row[f'{reference_gene} Average'], row[f'{reference_gene} Stdv']),
            axis=1
        )

        # 按 Target Name 和 Sample Name（数字大小）排序，参考基因优先
        def sort_key(row):
            target_name = row['Target Name']
            
            target_priority = self._get_target_priority(target_name)
            
            try:
                # 尝试将Sample Name转换为数字进行排序
                sample_num = float(row['Sample Name'])
                return (target_priority, target_name, sample_num)
            except (ValueError, TypeError):
                # 如果无法转换为数字，使用字符串排序
                return (target_priority, target_name, str(row['Sample Name']))
        
        base_df['sort_key'] = base_df.apply(sort_key, axis=1)
        base_df = base_df.sort_values('sort_key').drop('sort_key', axis=1).reset_index(drop=True)
        
        # 记录排序后的Target Name顺序
        target_order = base_df['Target Name'].drop_duplicates().tolist()
        self.logger.info(f"生成 {reference_gene} sheet，Target Name排序: {target_order}")

        # 在每个 Target 组之间插入空白行（默认6行），便于视觉分隔并左表右图对齐
        rows_with_blanks = []
        current_target = None
        warning_col = f'{reference_gene} Error Warning'
        
        for _, row in base_df.iterrows():
            if current_target is None:
                current_target = row['Target Name']
            if row['Target Name'] != current_target:
                # 插入N行空白行（N=6）
                for _n in range(6):
                    rows_with_blanks.append({
                        'Target Name': None,
                        'Sample Name': None,
                        'Experiment Name': None,
                        f'{reference_gene} Average': None,
                        f'{reference_gene} Stdv': None,
                        warning_col: None
                    })
                current_target = row['Target Name']
            rows_with_blanks.append(row.to_dict())

        result_df = pd.DataFrame(rows_with_blanks, columns=['Target Name', 'Sample Name', 'Experiment Name', f'{reference_gene} Average', f'{reference_gene} Stdv', warning_col])

        # 格式化数值列
        result_df = self._format_numeric_precision(result_df)

        return result_df
    
    def _add_charts_to_excel(self, output_path: str, data_dict: Dict[str, pd.DataFrame]):
        """
        向Excel文件添加图表
        
        Args:
            output_path (str): Excel文件路径
            data_dict (Dict[str, pd.DataFrame]): 原始数据字典
        """
        try:
            from openpyxl import load_workbook
            
            # 重新打开Excel文件添加图表
            workbook = load_workbook(output_path)
            
            # 为每个原始数据集的参考基因sheet添加图表
            for sheet_name, df in data_dict.items():
                for reference_gene in self.reference_genes:
                    ref_sheet_name = f"{sheet_name}({reference_gene})"
                    safe_ref_sheet_name = self._sanitize_sheet_name(ref_sheet_name)
                    
                    if safe_ref_sheet_name in workbook.sheetnames:
                        self._add_charts_by_target_name(workbook, safe_ref_sheet_name, reference_gene, df)
            
            # 为合并的参考基因sheet添加图表
            for reference_gene in self.reference_genes:
                merged_sheet_name = f"Merge({reference_gene})"
                safe_merged_sheet_name = self._sanitize_sheet_name(merged_sheet_name)
                
                if safe_merged_sheet_name in workbook.sheetnames:
                    # 为合并sheet添加图表，使用所有数据集的合并数据
                    merged_df = self._create_merged_df_for_charts(data_dict, reference_gene)
                    if not merged_df.empty:
                        self._add_charts_by_target_name(workbook, safe_merged_sheet_name, reference_gene, merged_df)
            
            workbook.save(output_path)
            self.logger.info("图表添加完成")
            
        except Exception as e:
            self.logger.error(f"添加图表失败: {e}")
    
    def _create_merged_df_for_charts(self, data_dict: Dict[str, pd.DataFrame], reference_gene: str) -> pd.DataFrame:
        """
        为合并的参考基因sheet创建用于图表的数据框
        
        Args:
            data_dict (Dict[str, pd.DataFrame]): 原始数据字典
            reference_gene (str): 参考基因名称
            
        Returns:
            pd.DataFrame: 合并后用于图表的数据框
        """
        try:
            # 合并所有原始数据
            all_dfs = []
            for sheet_name, df in data_dict.items():
                df_with_source = df.copy()
                df_with_source['Data Source'] = sheet_name
                all_dfs.append(df_with_source)
            
            if all_dfs:
                merged_df = pd.concat(all_dfs, ignore_index=True)
                return merged_df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"创建合并图表数据失败: {e}")
            return pd.DataFrame()
    
    def _add_charts_by_target_name(self, workbook, sheet_name: str, reference_gene: str, original_df: pd.DataFrame):
        """
        按照Target Name分组，为每个Target Name添加柱状图
        横坐标：Experiment Name，纵坐标：Normalized to reference_gene
        
        Args:
            workbook: openpyxl工作簿对象
            sheet_name (str): sheet名称
            reference_gene (str): 参考基因名称
            original_df (pd.DataFrame): 原始数据，用于分析Target Name分组
        """
        try:
            worksheet = workbook[sheet_name]
            
            # 获取所有唯一的Target Name
            average_col = f'{reference_gene} Average'
            stdv_col = f'{reference_gene} Stdv'
            
            required_cols = ['Target Name', 'Sample Name', 'Experiment Name', average_col, stdv_col]
            missing_cols = [col for col in required_cols if col not in original_df.columns]
            
            if missing_cols:
                self.logger.warning(f"缺少列 {missing_cols}，跳过为 {sheet_name} 添加图表")
                return
            
            # 按Target Name和Sample Name分组，获取每个组的代表数据
            grouped = original_df.groupby(['Target Name', 'Sample Name']).first().reset_index()
            
            # 按Sample Name数字大小排序
            def sort_sample_name(df):
                try:
                    # 尝试将Sample Name转换为数字进行排序
                    df['sample_num'] = pd.to_numeric(df['Sample Name'], errors='coerce')
                    # 先按数字排序，NaN值排在最后
                    df = df.sort_values(['Target Name', 'sample_num', 'Sample Name'], na_position='last')
                    df = df.drop('sample_num', axis=1)
                    return df
                except Exception:
                    # 如果排序失败，使用原始排序
                    return df.sort_values(['Target Name', 'Sample Name'])
            
            grouped = sort_sample_name(grouped)
            
            # 获取所有唯一的Target Name，并将参考基因排在最前面
            all_targets = grouped['Target Name'].unique()
            
            # 检查是否是合并sheet（sheet名包含"Merge"）
            is_merged_sheet = "Merge" in sheet_name
            
            if is_merged_sheet:
                # 对于合并sheet，按照worksheet中实际出现的Target Name顺序排序
                # 这样能保证参考基因在前面（因为合并数据时已经排序过了）
                worksheet_target_order = []
                seen_targets = set()
                for row_idx in range(2, worksheet.max_row + 1):
                    cell_value = worksheet.cell(row=row_idx, column=1).value
                    if cell_value and cell_value not in seen_targets and cell_value in all_targets:
                        worksheet_target_order.append(cell_value)
                        seen_targets.add(cell_value)
                
                # 使用worksheet中的顺序，确保参考基因在前
                unique_targets = worksheet_target_order
                self.logger.info(f"合并sheet {sheet_name} 中的Target排序（按worksheet顺序）: {unique_targets}")
            else:
                # 对于普通sheet，使用原有的排序逻辑
                # 将参考基因排在最前面，其他基因按原顺序排列
                reference_targets = []
                other_targets = []
                
                for target in all_targets:
                    if target in self.reference_genes:
                        reference_targets.append(target)
                    else:
                        other_targets.append(target)
                
                # 按参考基因在配置中的顺序排序参考基因
                sorted_reference_targets = []
                for ref_gene in self.reference_genes:
                    if ref_gene in reference_targets:
                        sorted_reference_targets.append(ref_gene)
                
                # 合并：参考基因在前，其他基因在后
                unique_targets = sorted_reference_targets + other_targets
                self.logger.info(f"普通sheet {sheet_name} 中的Target排序: 参考基因={sorted_reference_targets}, 其他基因={other_targets}")
            
            # 读取布局参数（左表右图模式：固定右侧列，行锚定到该Target的首行）
            right_col = int(self.chart_layout.get('right_col', self.chart_layout.get('start_col', 7)))
            
            # 区分内部图表区域大小和外部窗口大小
            chart_width = float(self.chart_layout.get('chart_width', 10))    # 内部绘图区域宽度
            chart_height = float(self.chart_layout.get('chart_height', 6))   # 内部绘图区域高度
            window_width = float(self.chart_layout.get('window_width', 15))  # 外部窗口总宽度
            window_height = float(self.chart_layout.get('window_height', 8)) # 外部窗口总高度
            plot_left_margin = float(self.chart_layout.get('plot_area_left_margin', 0.25))  # 绘图区域左边距
            bar_color = self.chart_layout.get('bar_color', '4472C4')         # 柱状图颜色
            grid_color = self.chart_layout.get('grid_line_color', 'D3D3D3')  # 网格线颜色

            # 为每个Target Name创建图表（对齐左侧表每个Target块的首行，右侧固定列）
            for i, target_name in enumerate(unique_targets):
                target_data = grouped[grouped['Target Name'] == target_name]
                
                if len(target_data) > 0:
                    # 扫描worksheet找到target的实际行位置（适用于所有sheet类型）
                    target_rows = []
                    for row_idx in range(2, worksheet.max_row + 1):
                        if worksheet.cell(row=row_idx, column=1).value == target_name:
                            target_rows.append(row_idx)
                    if not target_rows:
                        self.logger.warning(f"在sheet {sheet_name} 中找不到Target Name '{target_name}' 的数据")
                        continue
                    min_row = min(target_rows)
                    chart_anchor = f"{self._get_column_letter(right_col)}{min_row}"
                    
                    self.logger.info(f"Sheet {sheet_name}: {target_name} 图表位置={chart_anchor}, 实际起始行={min_row}")
                    
                    self._create_target_chart(
                        worksheet, target_name, target_data, reference_gene, chart_anchor, sheet_name,
                        chart_width=chart_width, chart_height=chart_height,
                        window_width=window_width, window_height=window_height,
                        plot_left_margin=plot_left_margin, bar_color=bar_color, grid_color=grid_color
                    )
            
            self.logger.info(f"在sheet {sheet_name} 中为 {len(unique_targets)} 个Target Name添加了柱状图")
            
        except Exception as e:
            self.logger.error(f"为sheet {sheet_name} 添加Target Name图表失败: {e}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def _get_column_letter(self, col_num: int) -> str:
        """
        将列号转换为Excel列字母（如1->A, 27->AA）
        
        Args:
            col_num (int): 列号（从1开始）
            
        Returns:
            str: Excel列字母
        """
        from openpyxl.utils import get_column_letter
        return get_column_letter(col_num)
    
    def _create_target_chart(self, worksheet, target_name: str, target_data: pd.DataFrame, reference_gene: str, chart_anchor: str, sheet_name: str, chart_width: float = 10.0, chart_height: float = 6.0, window_width: float = 15.0, window_height: float = 8.0, plot_left_margin: float = 0.25, bar_color: str = '4472C4', grid_color: str = 'D3D3D3'):
        """
        为单个Target Name创建柱状图
        
        Args:
            worksheet: Excel工作表对象
            target_name (str): 目标基因名称
            target_data (pd.DataFrame): 该Target Name的数据
            reference_gene (str): 参考基因名称
            chart_anchor (str): 图表锚点位置
            sheet_name (str): sheet名称
            chart_width (float): 内部绘图区域宽度
            chart_height (float): 内部绘图区域高度
            window_width (float): 外部窗口总宽度（包含标题、轴标签等）
            window_height (float): 外部窗口总高度（包含标题、轴标签等）
            plot_left_margin (float): 绘图区域左边距比例（0-1），用于避免Y轴标题与刻度重叠
            bar_color (str): 柱状图颜色，十六进制颜色代码
            grid_color (str): 网格线颜色，十六进制颜色代码
        """
        try:
            # 创建柱状图 - 使用最普通的样式
            chart = BarChart()
            chart.type = "col"
            chart.style = 2  # 使用简单的默认样式
            
            # 设置图表标题为Target Name
            chart.title = target_name
            
            # 设置Y轴（数值轴）
            chart.y_axis.title = f'Normalized to {reference_gene}'  # 恢复Y轴标题显示
            chart.y_axis.scaling.min = 0
            chart.y_axis.number_format = 'General'
            
            # 显示水平网格线，使用浅灰色
            from openpyxl.chart.axis import ChartLines
            from openpyxl.chart.shapes import GraphicalProperties
            
            gridlines = ChartLines()
            # 设置网格线为可配置的颜色和虚线
            grid_props = GraphicalProperties()
            grid_props.line.solidFill = grid_color  # 使用配置的网格线颜色
            grid_props.line.prstDash = 'dash'  # 虚线
            gridlines.spPr = grid_props
            chart.y_axis.majorGridlines = gridlines
            
            # 隐藏Y轴线条
            y_axis_props = GraphicalProperties()
            y_axis_props.noFill = True  # 隐藏Y轴线
            chart.y_axis.spPr = y_axis_props
            chart.y_axis.majorTickMark = 'none'  # 隐藏Y轴刻度线
            
            # 设置X轴（分类轴） - 不显示标题
            chart.x_axis.title = None  # 不显示横坐标标题
            chart.x_axis.majorGridlines = None  # 隐藏垂直网格线
            
            # 隐藏图例，仅显示标题与坐标轴
            chart.legend = None
            
            # 找到Target Name在worksheet中的数据行
            target_rows = []
            for row_idx in range(2, worksheet.max_row + 1):  # 从第2行开始（跳过标题）
                cell_value = worksheet.cell(row=row_idx, column=1).value  # Target Name在第1列
                if cell_value == target_name:
                    target_rows.append(row_idx)
            
            if not target_rows:
                self.logger.warning(f"在worksheet中找不到Target Name '{target_name}' 的数据")
                return
            
            # 构建数据范围
            min_row = min(target_rows)
            max_row = max(target_rows)
            
            # 添加数据到图表
            # Y轴数据：Average值 (第4列) - 包含标题行用于自动标签
            data = Reference(worksheet, min_col=4, min_row=min_row, max_row=max_row)
            chart.add_data(data, titles_from_data=False)
            
            # X轴标签：Experiment Name (第3列) - 确保正确读取标签
            categories = Reference(worksheet, min_col=3, min_row=min_row, max_row=max_row)
            chart.set_categories(categories)
            
            # 设置柱状图为统一的蓝色
            if len(chart.series) > 0:
                try:
                    series = chart.series[0]
                    
                    # 使用openpyxl的简单颜色设置
                    from openpyxl.chart.shapes import GraphicalProperties
                    
                    # 使用配置的柱状图颜色
                    series.graphicalProperties = GraphicalProperties(solidFill=bar_color)
                    
                    self.logger.info(f"为 {target_name} 设置了柱状图颜色: {bar_color}")
                except Exception as color_e:
                    self.logger.warning(f"设置柱状图颜色失败: {color_e}")
                    # 尝试更简单的方法
                    try:
                        # 直接在系列上设置颜色
                        chart.series[0].graphicalProperties = None  # 重置
                        self.logger.info(f"为 {target_name} 重置了图表样式为默认蓝色")
                    except Exception:
                        self.logger.warning(f"无法设置 {target_name} 的图表颜色")
            
            # 调试信息：记录数据范围和实际值
            self.logger.info(f"{target_name} 数据范围: 行{min_row}-{max_row}, Y轴列D, X轴列C")
            
            # 记录实际的X轴标签值用于调试
            x_labels = []
            y_values = []
            for row_idx in range(min_row, max_row + 1):
                x_val = worksheet.cell(row=row_idx, column=3).value  # Experiment Name
                y_val = worksheet.cell(row=row_idx, column=4).value  # Average
                if x_val is not None:
                    x_labels.append(str(x_val))
                if y_val is not None:
                    y_values.append(y_val)
            
            self.logger.info(f"{target_name} X轴标签: {x_labels}")
            self.logger.info(f"{target_name} Y轴数值: {y_values}")
            
            # 强制显示坐标轴和刻度标签
            chart.x_axis.delete = False
            chart.y_axis.delete = False
            chart.x_axis.tickLblPos = "low"
            chart.y_axis.tickLblPos = "low"
            
            # 根据内部绘图区域尺寸调整坐标轴样式
            try:
                # 根据chart_height调整Y轴刻度的数量
                height_ratio = chart_height / window_height
                if height_ratio < 0.5:  # 如果内部区域相对较小
                    # 减少Y轴刻度数量，让绘图更紧凑
                    if hasattr(chart.y_axis.scaling, 'max'):
                        chart.y_axis.scaling.max = None  # 让Excel自动调整
                    
                # 根据chart_width调整X轴标签样式
                width_ratio = chart_width / window_width
                if width_ratio < 0.5:  # 如果内部区域相对较小
                    # 可以考虑调整X轴标签的角度或大小
                    pass
                    
                self.logger.info(f"绘图区域比例调整: 宽度比例={width_ratio:.2f}, 高度比例={height_ratio:.2f}")
                    
            except Exception as axis_e:
                self.logger.warning(f"调整坐标轴样式失败: {axis_e}")
            
            # 确保显示X轴刻度线，Y轴刻度线已经在前面设置为none（隐藏）
            chart.x_axis.majorTickMark = "out"  # 显示X轴主刻度
            chart.y_axis.majorTickMark = "out"  # 显示主刻度
            
            # 设置图表位置
            chart.anchor = chart_anchor
            
            # 设置图表外部窗口总尺寸（包含标题、轴标签等所有元素）
            chart.width = int(window_width)
            chart.height = int(window_height)
            
            # 尝试通过调整图表样式来影响内部绘图区域
            try:
                # 计算柱子宽度和间距，间接控制绘图区域的使用
                if len(chart.series) > 0:
                    series = chart.series[0]
                    
                    # 根据chart_width相对于window_width的比例来调整柱子间距
                    width_ratio = chart_width / window_width
                    
                    # 调整柱子间的间距（gap）
                    if hasattr(chart, 'gapWidth'):
                        # gapWidth: 柱子间的间距，数值越大间距越大，绘图区域使用越少
                        base_gap = 150  # 默认间距
                        adjusted_gap = int(base_gap * (1 / width_ratio))
                        chart.gapWidth = min(500, max(50, adjusted_gap))  # 限制在50-500之间
                        
                        self.logger.info(f"为 {target_name} 调整柱子间距: {chart.gapWidth} (比例: {width_ratio:.2f})")
                    
                    # 尝试调整柱子的重叠度
                    if hasattr(chart, 'overlap'):
                        chart.overlap = 0  # 柱子不重叠
                
            except Exception as style_e:
                self.logger.warning(f"调整图表样式失败: {style_e}")
            
            # 记录图表配置信息
            self.logger.info(f"为 {target_name} 设置图表: 外部窗口={window_width}x{window_height}, 内部区域参考={chart_width}x{chart_height}")
            
            # 添加误差线 - 必须在add_data之后，add_chart之前
            try:
                if len(chart.series) > 0:
                    series = chart.series[0]
                    
                    # 先检查误差线数据的值
                    error_values = []
                    for row_idx in range(min_row, max_row + 1):
                        error_val = worksheet.cell(row=row_idx, column=5).value  # 第5列是Stdv
                        if error_val is not None:
                            error_values.append(error_val)
                    
                    self.logger.info(f"{target_name} 误差线数据值: {error_values}")
                    
                    # 创建误差线对象，使用完整的属性设置
                    error_bars = ErrorBars()
                    
                    # 基本属性
                    error_bars.errDir = 'y'           # 垂直方向
                    error_bars.errBarType = 'both'    # 上下都显示
                    error_bars.errValType = 'cust'    # 自定义值类型
                    error_bars.noEndCap = False       # 显示端帽
                    
                    # 使用Stdv列作为误差值 (第5列)
                    from openpyxl.chart.data_source import NumDataSource, NumRef
                    num_ref = NumRef(f"'{sheet_name}'!$E${min_row}:$E${max_row}")
                    error_data_source = NumDataSource(numRef=num_ref)
                    
                    # 设置正负误差值
                    error_bars.plus = error_data_source
                    error_bars.minus = error_data_source
                    
                    # 将误差线添加到系列
                    series.errBars = error_bars
                    
                    self.logger.info(f"为 {target_name} 图表添加了误差线，数据范围: E{min_row}:E{max_row}")
            except Exception as e:
                self.logger.warning(f"为 {target_name} 添加误差线失败: {e}")
                import traceback
                self.logger.warning(f"误差线错误详情: {traceback.format_exc()}")
            
            # 设置绘图区域的布局，将其向右移动以避免Y轴标题与刻度重叠
            try:
                from openpyxl.chart.layout import Layout, ManualLayout
                
                # 创建手动布局
                layout = Layout()
                manual_layout = ManualLayout()
                
                # 设置绘图区域位置和大小
                manual_layout.x = plot_left_margin      # 左边距，将绘图区域向右移动
                manual_layout.y = 0.1                   # 上边距10%
                manual_layout.w = 1.0 - plot_left_margin - 0.1  # 宽度：剩余空间减去右边距
                manual_layout.h = 0.8                   # 高度80%
                
                layout.manualLayout = manual_layout
                
                # 尝试设置布局（不同版本的openpyxl可能有不同的API）
                if hasattr(chart, 'layout'):
                    chart.layout = layout
                    self.logger.info(f"为 {target_name} 设置图表布局: 左边距={plot_left_margin:.2f}")
                else:
                    self.logger.warning(f"当前openpyxl版本不支持chart.layout，尝试其他方法")
                    
            except Exception as layout_e:
                self.logger.warning(f"设置图表布局失败: {layout_e}")
            
            # 添加图表到工作表
            worksheet.add_chart(chart)
            
            self.logger.info(f"为Target Name '{target_name}' 添加了柱状图，位置: {chart_anchor}")
            
        except Exception as e:
            self.logger.error(f"为Target Name '{target_name}' 创建图表失败: {e}")
        