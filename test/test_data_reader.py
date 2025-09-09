"""
数据读取器测试模块
"""
import unittest
import pandas as pd
import os
import tempfile
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_reader import DataReader

class TestDataReader(unittest.TestCase):
    """数据读取器测试类"""
    
    def setUp(self):
        """测试设置"""
        self.test_dir = tempfile.mkdtemp()
        self.reader = DataReader(self.test_dir)
        
        # 创建测试Excel文件
        self.test_data = pd.DataFrame({
            'Experiment Name': ['Exp1', 'Exp2'],
            'Well Position': ['A1', 'A2'],
            'Target Name': ['GAPDH', 'TBP'],
            'Sample Name': ['Sample1', 'Sample2'],
            'CT': [20.5, 25.3]
        })
        
        self.test_file_path = os.path.join(self.test_dir, 'P1 test.xlsx')
        
        # 创建一个包含Results sheet的Excel文件
        with pd.ExcelWriter(self.test_file_path, engine='openpyxl') as writer:
            self.test_data.to_excel(writer, sheet_name='Results', index=False)
    
    def tearDown(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_extract_file_prefix(self):
        """测试文件前缀提取"""
        test_cases = [
            ('P1 2025-07-28 160758.xls', 'P1'),
            ('P2 2025-07-29 101649.xls', 'P2'),
            ('single_word.xls', 'single_word')
        ]
        
        for file_path, expected in test_cases:
            with self.subTest(file_path=file_path):
                result = self.reader.extract_file_prefix(file_path)
                self.assertEqual(result, expected)
    
    def test_get_file_list(self):
        """测试获取文件列表"""
        file_list = self.reader.get_file_list()
        self.assertEqual(len(file_list), 1)
        self.assertTrue(file_list[0].endswith('P1 test.xlsx'))
    
    def test_read_excel_data(self):
        """测试读取Excel数据"""
        df = self.reader.read_excel_data(self.test_file_path)
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertListEqual(list(df.columns), list(self.test_data.columns))
    
    def test_extract_required_columns(self):
        """测试提取所需列"""
        df = self.reader.read_excel_data(self.test_file_path)
        extracted_df = self.reader.extract_required_columns(df)
        
        expected_columns = ['Experiment Name', 'Well Position', 'Target Name', 'Sample Name', 'CT']
        self.assertListEqual(list(extracted_df.columns), expected_columns)
        self.assertEqual(len(extracted_df), 2)

if __name__ == '__main__':
    unittest.main()
