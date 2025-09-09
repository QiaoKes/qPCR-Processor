"""
主程序模块
协调整个数据处理流程
"""
import logging
import os
from typing import Dict
import pandas as pd

from data_reader import DataReader
from data_processor import DataProcessor
from data_writer import DataWriter

class ExperimentDataProcessor:
    """实验数据处理主类"""
    
    def __init__(self, src_dir: str, dst_dir: str, config_dir: str):
        """
        初始化实验数据处理器
        
        Args:
            src_dir (str): 源数据目录
            dst_dir (str): 目标数据目录
            config_dir (str): 配置文件目录
        """
        self.src_dir = src_dir
        self.dst_dir = dst_dir
        self.config_dir = config_dir
        
        # 初始化各个组件
        self.data_reader = DataReader(src_dir)
        config_path = os.path.join(config_dir, 'sample_mapping.json')
        self.data_processor = DataProcessor(config_path)
        self.data_writer = DataWriter(dst_dir, config_path)
        
        # 配置日志
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
    
    def _setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('experiment_processor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def process_all_files(self) -> Dict[str, pd.DataFrame]:
        """
        处理所有文件
        
        Returns:
            Dict[str, pd.DataFrame]: 处理后的数据字典
        """
        self.logger.info("开始处理所有文件...")
        
        # 获取所有文件
        file_list = self.data_reader.get_file_list()
        if not file_list:
            self.logger.warning("未找到任何xls文件")
            return {}
        
        processed_data = {}
        
        for file_path in file_list:
            try:
                # 提取文件前缀作为sheet名称
                sheet_name = self.data_reader.extract_file_prefix(file_path)
                
                # 读取数据
                raw_data = self.data_reader.read_excel_data(file_path)
                if raw_data.empty:
                    self.logger.warning(f"文件 {file_path} 无数据，跳过")
                    continue
                
                # 提取所需列
                extracted_data = self.data_reader.extract_required_columns(raw_data)
                
                # 应用样本映射（传递文件前缀）
                mapped_data = self.data_processor.apply_sample_mapping(extracted_data, sheet_name)
                
                # 处理CT值
                processed_ct = self.data_processor.process_ct_values(mapped_data)
                
                # 计算扩展指标
                final_data = self.data_processor.calculate_extended_metrics(processed_ct)
                
                processed_data[sheet_name] = final_data
                self.logger.info(f"文件 {file_path} 处理完成，生成sheet: {sheet_name}")
                
            except Exception as e:
                self.logger.error(f"处理文件 {file_path} 时出错: {e}")
                continue
        
        return processed_data
    
    def save_results(self, processed_data: Dict[str, pd.DataFrame]):
        """
        保存处理结果
        
        Args:
            processed_data (Dict[str, pd.DataFrame]): 处理后的数据
        """
        if not processed_data:
            self.logger.warning("没有数据需要保存")
            return
        
        # 保存到单个Excel文件的多个sheet中
        output_path = self.data_writer.write_to_excel(processed_data)
        if output_path:
            self.logger.info(f"所有数据已保存到: {output_path}")
        
        # 可选：保存为单独的文件
        # self.data_writer.save_individual_files(processed_data)
    
    def run(self):
        """运行完整的处理流程"""
        try:
            self.logger.info("=== 开始实验数据处理 ===")
            
            # 处理所有文件
            processed_data = self.process_all_files()
            
            # 保存结果
            self.save_results(processed_data)
            
            self.logger.info("=== 实验数据处理完成 ===")
            
        except Exception as e:
            self.logger.error(f"处理流程出错: {e}")
            raise

def main():
    """主函数"""
    # 设置路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    src_dir = os.path.join(project_root, 'src_data')
    dst_dir = os.path.join(project_root, 'dst_data')
    config_dir = os.path.join(project_root, 'config')
    
    # 创建处理器并运行
    processor = ExperimentDataProcessor(src_dir, dst_dir, config_dir)
    processor.run()

if __name__ == "__main__":
    main()
