"""
集成测试模块
测试完整的数据处理流程
"""
import unittest
import pandas as pd
import os
import tempfile
import json
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import ExperimentDataProcessor

class TestIntegration(unittest.TestCase):
    """集成测试类"""
    
    def setUp(self):
        """测试设置"""
        # 创建临时目录结构
        self.test_root = tempfile.mkdtemp()
        self.src_dir = os.path.join(self.test_root, 'src_data')
        self.dst_dir = os.path.join(self.test_root, 'dst_data')
        self.config_dir = os.path.join(self.test_root, 'config')
        
        os.makedirs(self.src_dir)
        os.makedirs(self.dst_dir)
        os.makedirs(self.config_dir)
        
        # 创建测试数据文件
        self.create_test_data_files()
        
        # 创建配置文件
        self.create_config_file()
        
        # 创建处理器
        self.processor = ExperimentDataProcessor(self.src_dir, self.dst_dir, self.config_dir)
    
    def tearDown(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.test_root)
    
    def create_test_data_files(self):
        """创建测试数据文件"""
        # P1 文件数据
        p1_data = pd.DataFrame({
            'Experiment Name': ['Exp1'] * 6,
            'Well Position': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
            'Target Name': ['GAPDH', 'GAPDH', 'TBP', 'TBP', 'Gene1', 'Gene1'],
            'Sample Name': ['Sample1', 'Sample2', 'Sample1', 'Sample2', 'Sample1', 'Sample2'],
            'CT': [20.0, 22.0, 25.0, 'Undetermined', 30.0, 32.0]
        })
        
        # P2 文件数据
        p2_data = pd.DataFrame({
            'Experiment Name': ['Exp2'] * 4,
            'Well Position': ['A1', 'A2', 'B1', 'B2'],
            'Target Name': ['GAPDH', 'GAPDH', 'TBP', 'TBP'],
            'Sample Name': ['Sample3', 'Sample4', 'Sample3', 'Sample4'],
            'CT': [19.5, 21.5, 24.0, 26.0]
        })
        
        # 保存文件
        p1_path = os.path.join(self.src_dir, 'P1 2025-07-28 160758.xlsx')
        p2_path = os.path.join(self.src_dir, 'P2 2025-07-29 101649.xlsx')
        
        with pd.ExcelWriter(p1_path, engine='openpyxl') as writer:
            p1_data.to_excel(writer, sheet_name='Results', index=False)
        
        with pd.ExcelWriter(p2_path, engine='openpyxl') as writer:
            p2_data.to_excel(writer, sheet_name='Results', index=False)
    
    def create_config_file(self):
        """创建配置文件"""
        config = {
            'sample_mapping': {
                'Sample1': 'Control_Group_1',
                'Sample2': 'Control_Group_2',
                'Sample3': 'Treatment_Group_1',
                'Sample4': 'Treatment_Group_2'
            },
            'reference_genes': ['GAPDH', 'TBP']
        }
        
        config_path = os.path.join(self.config_dir, 'sample_mapping.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def test_complete_processing_workflow(self):
        """测试完整的处理工作流程"""
        # 运行处理流程
        processed_data = self.processor.process_all_files()
        
        # 检查是否处理了两个文件
        self.assertEqual(len(processed_data), 2)
        self.assertIn('P1', processed_data)
        self.assertIn('P2', processed_data)
        
        # 检查P1数据
        p1_result = processed_data['P1']
        self.assertGreater(len(p1_result), 0)
        
        # 检查是否包含所需的列
        expected_columns = [
            'Experiment Name', 'Well Position', 'Target Name', 'Sample Name', 'CT',
            'Ct Mean', '', 'GAPDH Cq mean', 'GAPDH ΔCT', 'GAPDH 2^(-ΔCT)',
            'GAPDH Average', 'GAPDH Stdv', ' ', 'TBP Cq mean', 'TBP ΔCT',
            'TBP 2^(-ΔCT)', 'TBP Average', 'TBP Stdv'
        ]
        
        for col in expected_columns:
            self.assertIn(col, p1_result.columns, f"缺少列: {col}")
        
        # 检查样本映射是否生效
        mapped_names = p1_result['Experiment Name'].unique()
        self.assertIn('Control_Group_1', mapped_names)
        self.assertIn('Control_Group_2', mapped_names)
    
    def test_save_results(self):
        """测试保存结果"""
        # 处理数据
        processed_data = self.processor.process_all_files()
        
        # 保存结果
        self.processor.save_results(processed_data)
        
        # 检查输出文件是否存在
        output_file = os.path.join(self.dst_dir, 'processed_data.xlsx')
        self.assertTrue(os.path.exists(output_file))
        
        # 检查文件内容
        with pd.ExcelFile(output_file) as excel_file:
            sheet_names = excel_file.sheet_names
            self.assertIn('P1', sheet_names)
            self.assertIn('P2', sheet_names)
    
    def test_ct_value_processing(self):
        """测试CT值特殊处理逻辑"""
        processed_data = self.processor.process_all_files()
        p1_data = processed_data['P1']
        
        # 检查Undetermined值是否被正确处理
        # 在我们的测试数据中，TBP的Sample2有一个Undetermined值
        tbp_sample2_data = p1_data[
            (p1_data['Target Name'] == 'TBP') & 
            (p1_data['Sample Name'] == 'Sample2')
        ]
        
        # 应该存在数据且CT值不应该是'Undetermined'字符串
        self.assertGreater(len(tbp_sample2_data), 0)
        ct_values = tbp_sample2_data['CT'].values
        for ct in ct_values:
            self.assertNotEqual(ct, 'Undetermined')

if __name__ == '__main__':
    unittest.main()
