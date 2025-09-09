# qPCR-Processor

[English Documentation](README.md) | [中文文档](README_CN.md)

一个基于Python的qPCR（定量聚合酶链反应）实验数据处理工具。该处理器从Excel文件中读取原始qPCR数据，使用参考基因进行标准化计算，并生成带有图表的格式化输出。

## 功能特性

- 自动读取Excel文件中的qPCR数据（.xls/.xlsx格式）
- 样本名称映射到实验名称
- 使用参考基因进行标准化（默认GAPDH、TBP）
- 基于标准差阈值的错误检测和告警
- 自动在Excel输出中生成柱状图
- 完整的日志记录用于调试和监控

## 安装方法

### 前置要求

- Python 3.7 或更高版本
- pip 包管理器

### 安装步骤

1. 将此仓库克隆或下载到本地计算机。
2. 导航到项目目录：

   ```bash
   cd qPCR-Processor
   ```
3. 安装所需的Python包：

   ```bash
   pip install -r requirements.txt
   ```

   或者使用提供的安装脚本：

   - **Windows**：双击 `install-win.bat`
   - **macOS/Linux**：运行 `./install-mac-linux.sh`

## 使用方法

### 运行处理器

1. 将qPCR数据文件按照命名规范放置在 `src_data/` 目录中（见下文）。
2. 根据需要配置 `config/sample_mapping.json` 中的样本映射。
3. 运行处理器：

   ```bash
   python src/main.py
   ```

   或者使用提供的启动脚本：

   - **Windows**：双击 `start-win.bat`
   - **macOS/Linux**：运行 `./start-mac-linux.sh`
4. 在 `dst_data/` 目录中查看输出文件（自动创建）。
5. 查看 `experiment_processor.log` 中的日志以获取处理详情。

### 文件命名规范

`src_data/` 中的输入Excel文件必须遵循以下格式：

```
{前缀} {日期} {时间}.xls
```

示例：

- `P1 2025-07-28 160758.xls`
- `P2 1999-01-02 237342.xls`

**前缀**（第一个空格前的部分）用于在 `config/sample_mapping.json` 中映射样本到实验名称。

### Excel文件格式

- **工作表名称**：必须包含名为"Results"的工作表
- **数据结构**：处理器将自动跳过无效的标题行并提取以下列：
  - `Experiment Name`（实验名称）
  - `Well Position`（孔位）
  - `Target Name`（靶基因名称）
  - `Sample Name`（样本名称）
  - `CT`（循环阈值）

## 配置说明

### sample_mapping.json字段含义

`config/sample_mapping.json` 文件包含几个重要的配置部分：

#### `sample_mapping`

按文件前缀分组，将样本名称映射到实验名称：

```json
{
  "P1": {
    "1": "E01",
    "2": "E02",
    ...
  },
  "P2": {
    "1": "E13",
    "2": "E14",
    ...
  }
}
```

- **文件前缀**：文件名中第一个空格前的部分（例如，从"P1 2025-07-28 160758.xls"中提取"P1"）
- **样本名称**：Excel文件中的原始样本标识符
- **实验名称**：输出中使用的实验标识符（E01-E24，为脱敏处理使用编码名称）

#### `reference_genes`

用于标准化的参考基因列表：

```json
["GAPDH", "TBP"]
```

可根据需要添加更多参考基因，如"ACTB"。

#### `error_threshold`

错误告警阈值（标准差作为平均值的倍数）：

```json
0.3
```

当标准差超过平均值的30%时发出告警。

#### `chart_layout`

Excel中柱状图的布局配置参数：

- `start_col`：图表起始列位置（Excel列索引）
- `chart_width`/`chart_height`：绘图区域尺寸
- `window_width`/`window_height`：图表窗口总尺寸
- `plot_area_left_margin`：绘图区域左边距比例
- `bar_color`：柱状图颜色（十六进制颜色代码，如"4472C4"为蓝色）
- `grid_line_color`：网格线颜色（十六进制颜色代码，如"D3D3D3"为浅灰色）

## 输出结果

- 包含标准化计算的处理后数据文件
- 每个靶基因的柱状图
- 超过阈值的数据点的错误告警
- 完整的处理日志

## 故障排除

- 检查 `experiment_processor.log` 中的详细错误信息
- 确保Excel文件包含"Results"工作表和所需列
- 验证文件命名遵循指定规范
- 确认样本映射配置与您的数据匹配

## 许可证

详见LICENSE文件。
