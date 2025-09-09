"""
数据写入器测试模块
"""
import unittest
import pandas as pd
import os
import tempfile
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_writer import DataWriter

class TestDataWriter(unittest.TestCase):
    """数据写入器测试类"""
    
    def setUp(self):
        """测试设置"""
        self.test_dir = tempfile.mkdtemp()
        self.writer = DataWriter(self.test_dir)
        
        # 创建测试数据
        self.test_data = {
            'P1': pd.DataFrame({
                'Sample Name': ['Sample1', 'Sample2'],
                'Target Name': ['GAPDH', 'TBP'],
                'CT': [20.5, 25.3]
            }),
            'P2': pd.DataFrame({
                'Sample Name': ['Sample3', 'Sample4'],
                'Target Name': ['GAPDH', 'TBP'],
                'CT': [22.1, 24.8]
            })
        }
    
    def tearDown(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_sanitize_sheet_name(self):
        """测试sheet名称清理"""
        test_cases = [
            ('P1/test', 'P1_test'),
            ('P2\\data', 'P2_data'),
            ('P3?name', 'P3_name'),
            ('P4*file', 'P4_file'),
            ('P5[sheet]', 'P5_sheet_'),
            ('a' * 35, 'a' * 31),  # 测试长度限制
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.writer._sanitize_sheet_name(input_name)
                self.assertEqual(result, expected)
    
    def test_write_to_excel(self):
        """测试写入Excel文件"""
        output_path = self.writer.write_to_excel(self.test_data, 'test_output.xlsx')
        
        # 检查文件是否创建
        self.assertIsNotNone(output_path)
        if output_path:
            self.assertTrue(os.path.exists(output_path))
            
            # 检查文件内容
            with pd.ExcelFile(output_path) as excel_file:
                sheet_names = excel_file.sheet_names
                self.assertIn('P1', sheet_names)
                self.assertIn('P2', sheet_names)
                
                # 检查数据内容
                p1_data = pd.read_excel(output_path, sheet_name='P1')
                self.assertEqual(len(p1_data), 2)
                self.assertListEqual(list(p1_data.columns), ['Sample Name', 'Target Name', 'CT'])
    
    def test_save_individual_files(self):
        """测试保存单独文件"""
        self.writer.save_individual_files(self.test_data)
        
        # 检查是否创建了单独的文件
        expected_files = ['P1_processed.xlsx', 'P2_processed.xlsx']
        for filename in expected_files:
            file_path = os.path.join(self.test_dir, filename)
            self.assertTrue(os.path.exists(file_path))
            
            # 检查文件内容
            df = pd.read_excel(file_path)
            self.assertEqual(len(df), 2)

if __name__ == '__main__':
    unittest.main()
