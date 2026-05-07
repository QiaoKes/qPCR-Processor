"""
数据处理器测试模块
"""
import unittest
import pandas as pd
import numpy as np
import os
import tempfile
import json
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    """数据处理器测试类"""
    
    def setUp(self):
        """测试设置"""
        self.processor = DataProcessor()
        
        # 创建测试数据
        self.test_data = pd.DataFrame({
            'Experiment Name': ['Exp1', 'Exp1', 'Exp2', 'Exp2'],
            'Well Position': ['A1', 'A2', 'B1', 'B2'],
            'Target Name': ['GAPDH', 'TBP', 'GAPDH', 'TBP'],
            'Sample Name': ['Sample1', 'Sample1', 'Sample2', 'Sample2'],
            'CT': [20.5, 'Undetermined', 22.0, 25.3]
        })
        
        # 创建配置文件
        self.config_dir = tempfile.mkdtemp()
        self.config_data = {
            'sample_mapping': {
                'Sample1': 'Experiment_A',
                'Sample2': 'Experiment_B'
            },
            'reference_genes': ['GAPDH', 'TBP']
        }
        self.config_path = os.path.join(self.config_dir, 'test_config.json')
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f)
    
    def tearDown(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.config_dir)
    
    def test_load_config(self):
        """测试配置加载"""
        processor = DataProcessor(self.config_path)
        self.assertEqual(processor.sample_mapping['Sample1'], 'Experiment_A')
        self.assertEqual(processor.sample_mapping['Sample2'], 'Experiment_B')
        # 测试参考基因配置
        self.assertEqual(processor.reference_genes, ['GAPDH', 'TBP'])
    
    def test_set_reference_genes(self):
        """测试设置参考基因"""
        processor = DataProcessor()
        new_genes = ['ACTB', 'HPRT1', 'RPL32']
        processor.set_reference_genes(new_genes)
        self.assertEqual(processor.get_reference_genes(), new_genes)
    
    def test_custom_reference_genes_calculation(self):
        """测试自定义参考基因计算"""
        processor = DataProcessor()
        processor.set_reference_genes(['ACTB'])  # 只使用一个参考基因
        
        test_data = pd.DataFrame({
            'Sample Name': ['Sample1', 'Sample1', 'Sample2', 'Sample2'],
            'Target Name': ['ACTB', 'Gene1', 'ACTB', 'Gene1'],
            'CT': [18.0, 22.0, 19.0, 24.0]
        })
        
        result = processor.calculate_extended_metrics(test_data)
        
        # 检查是否包含ACTB相关的列
        expected_actb_columns = ['ACTB Cq mean', 'ACTB ΔCT', 'ACTB 2^(-ΔCT)', 'ACTB Average', 'ACTB Stdv']
        for col in expected_actb_columns:
            self.assertIn(col, result.columns)
    
    def test_apply_sample_mapping(self):
        """测试样本映射"""
        processor = DataProcessor(self.config_path)
        mapped_data = processor.apply_sample_mapping(self.test_data)
        
        # 检查映射是否正确应用
        self.assertEqual(mapped_data.loc[0, 'Experiment Name'], 'Experiment_A')
        self.assertEqual(mapped_data.loc[2, 'Experiment Name'], 'Experiment_B')
    
    def test_apply_sample_mapping_numeric_sample_names(self):
        """测试数字样本名能匹配字符串映射键"""
        processor = DataProcessor()
        processor.sample_mapping = {
            'P1': {
                '1': 'Experiment_1',
                '2': 'Experiment_2',
                'Control': 'Experiment_Control'
            }
        }
        test_data = pd.DataFrame({
            'Sample Name': [1.0, 1, '1', '2.0', 'Control', 3.0],
            'Target Name': ['GAPDH'] * 6,
            'CT': [20.0, 21.0, 22.0, 23.0, 24.0, 25.0]
        })
        
        mapped_data = processor.apply_sample_mapping(test_data, file_prefix='P1')
        
        self.assertEqual(mapped_data.loc[0, 'Experiment Name'], 'Experiment_1')
        self.assertEqual(mapped_data.loc[1, 'Experiment Name'], 'Experiment_1')
        self.assertEqual(mapped_data.loc[2, 'Experiment Name'], 'Experiment_1')
        self.assertEqual(mapped_data.loc[3, 'Experiment Name'], 'Experiment_2')
        self.assertEqual(mapped_data.loc[4, 'Experiment Name'], 'Experiment_Control')
        self.assertEqual(mapped_data.loc[5, 'Experiment Name'], 3.0)
    
    def test_process_ct_values_all_undetermined(self):
        """测试全为Undetermined的CT值处理"""
        # 创建全为Undetermined的测试数据（同一样本的同一基因）
        test_data = pd.DataFrame({
            'Sample Name': ['Sample1', 'Sample1'],
            'Target Name': ['GAPDH', 'GAPDH'],
            'CT': ['Undetermined', 'Undetermined']
        })
        
        processed_data = self.processor.process_ct_values(test_data)
        
        # 检查是否都设置为0
        self.assertTrue(all(processed_data['CT'] == 0))
    
    def test_process_ct_values_mixed(self):
        """测试混合CT值处理"""
        test_data = pd.DataFrame({
            'Sample Name': ['Sample1', 'Sample1', 'Sample1'],
            'Target Name': ['GAPDH', 'GAPDH', 'GAPDH'],
            'CT': [20.0, 22.0, 'Undetermined']
        })
        
        processed_data = self.processor.process_ct_values(test_data)
        
        # 检查Undetermined是否被替换为平均值
        expected_mean = 21.0  # (20.0 + 22.0) / 2
        self.assertEqual(processed_data.iloc[2]['CT'], expected_mean)
    
    def test_sample_name_grouping(self):
        """测试按Sample Name分组的逻辑"""
        test_data = pd.DataFrame({
            'Sample Name': ['Sample1', 'Sample1', 'Sample1', 'Sample2', 'Sample2'],
            'Target Name': ['GAPDH', 'GAPDH', 'TBP', 'GAPDH', 'TBP'],
            'CT': [20.0, 22.0, 25.0, 'Undetermined', 'Undetermined']
        })
        
        processed_data = self.processor.process_ct_values(test_data)
        
        # Sample1的GAPDH应该有一个计算出的平均值
        sample1_gapdh = processed_data[
            (processed_data['Sample Name'] == 'Sample1') & 
            (processed_data['Target Name'] == 'GAPDH')
        ]['CT'].values
        self.assertEqual(sample1_gapdh[0], 20.0)
        self.assertEqual(sample1_gapdh[1], 22.0)
        
        # Sample2的基因如果都是Undetermined，应该设置为0
        sample2_gapdh = processed_data[
            (processed_data['Sample Name'] == 'Sample2') & 
            (processed_data['Target Name'] == 'GAPDH')
        ]['CT'].values[0]
        self.assertEqual(sample2_gapdh, 0)
    
    def test_calculate_extended_metrics(self):
        """测试扩展指标计算"""
        # 准备数据
        test_data = pd.DataFrame({
            'Sample Name': ['Sample1', 'Sample1', 'Sample2', 'Sample2'],
            'Target Name': ['GAPDH', 'TBP', 'GAPDH', 'TBP'],
            'CT': [20.0, 25.0, 22.0, 27.0]
        })
        
        result = self.processor.calculate_extended_metrics(test_data)
        
        # 检查是否包含所需的列
        expected_columns = [
            'Ct Mean', '', 'GAPDH Cq mean', 'GAPDH ΔCT', 
            'GAPDH 2^(-ΔCT)', 'GAPDH Average', 'GAPDH Stdv',
            ' ', 'TBP Cq mean', 'TBP ΔCT', 
            'TBP 2^(-ΔCT)', 'TBP Average', 'TBP Stdv'
        ]
        
        for col in expected_columns:
            self.assertIn(col, result.columns)
        
        # 检查Ct Mean计算
        sample1_gapdh_mean = result[
            (result['Sample Name'] == 'Sample1') & 
            (result['Target Name'] == 'GAPDH')
        ]['Ct Mean'].iloc[0]
        self.assertEqual(sample1_gapdh_mean, 20.0)

if __name__ == '__main__':
    unittest.main()
