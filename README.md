# 光伏电站智能选址数据可视化大屏

一个基于3D地图和机器学习的光伏电站选址决策支持系统，提供直观的数据可视化和智能分析功能。
<img width="1920" height="869" alt="image" src="https://github.com/user-attachments/assets/9a07543e-774b-4579-89c0-dc5edfd33bb2" />


## 🌟 功能特色

### 核心功能
- **选址态势**：3D交互式中国地图，展示全国光伏电站分布
- **资源收益评估**：多维度分析光伏资源潜力和经济效益
- **实时选址**：基于AI模型的实时选址推荐

### 技术亮点
- 🎨 **3D地图可视化**：基于Three.js的高性能3D地图渲染
- 🤖 **AI智能选址**：GAT + GBDT集成模型，精准预测选址潜力
- 📊 **丰富图表**：ECharts驱动的多维度数据展示
- 🏙️ **省级下钻**：支持点击省份查看城市级详细信息
- 💡 **数据驱动**：结合地理信息、气象数据等多源数据

## 🏗️ 项目架构

```
.
├── api_server.py              # 基础API服务
├── api_server_full.py         # 完整API服务（含AI模型）
├── requirements.txt           # Python依赖
├── dashboard/                 # 前端可视化
│   ├── src/
│   │   ├── App.vue           # 主应用组件
│   │   └── components/
│   │       └── ThreeChinaMap.vue  # 3D地图组件
│   ├── package.json
│   └── vite.config.js
├── models/                    # 机器学习模型
├── CPVPD-2024_4326/          # 地理数据
└── solar_data_output/        # 输出数据
```

## 🛠️ 技术栈

### 前端
- **Vue 3** - 渐进式JavaScript框架
- **Three.js** - 3D图形库
- **ECharts** - 数据可视化库
- **Vite** - 下一代前端构建工具
- **D3.js** - 地理数据处理

### 后端
- **Python** - 主要编程语言
- **Flask** - Web框架
- **PyTorch / PyTorch Geometric** - 深度学习框架
- **Scikit-learn** - 机器学习库
- **GeoPandas** - 地理空间数据处理

### 数据与模型
- **GAT (Graph Attention Network)** - 图注意力网络
- **GBDT (Gradient Boosting Decision Tree)** - 梯度提升决策树
- **PVPI (Photovoltaic Potential Index)** - 光伏潜力指数

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 后端启动

1. 安装Python依赖：
```bash
pip install -r requirements.txt
```

2. 启动API服务：
```bash
python api_server_full.py
```

### 前端启动

1. 进入前端目录：
```bash
cd dashboard
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

4. 构建生产版本：
```bash
npm run build
```

## 📊 数据说明

### 核心指标
- **PVPI指数**：光伏潜力综合评分
- **GHI辐照**：水平面总辐照量
- **可建设面积**：适宜建设光伏电站的土地面积
- **电站数量**：现有光伏电站统计

### 数据文件
项目数据文件位于 `dashboard/public/data/`：
- `china_full.json` - 中国地理边界数据
- `provincial_statistics.csv` - 省级统计数据
- `pv_stations_mcdm_scored.csv` - 光伏电站评分数据

## 🤖 AI模型

### 模型架构
系统采用GAT + GBDT集成模型：
- **GAT模型**：捕捉地理空间依赖关系
- **GBDT模型**：处理结构化特征
- **集成策略**：加权融合双模型预测结果

### 模型输入特征
- 气象数据（辐照、温度、降水等）
- 地理特征（海拔、坡度、坡向等）
- 社会经济因素（土地成本、电网接入等）

## 🎯 使用说明

### 基本操作
1. **视图切换**：顶部标签页切换不同功能模块
2. **地图交互**：
   - 滚轮缩放
   - 拖拽平移
   - 左键点击省份进入城市视图
   - 右键返回全国视图
3. **数据探索**：通过侧边栏面板深入分析各维度数据

### 选址流程
1. 查看全国光伏资源分布态势
2. 筛选高潜力省份
3. 进入省级视图查看城市详情
4. 结合AI推荐和数据分析确定最佳选址

## 🔧 开发指南

### 项目结构说明
- `api_server_full.py` - 完整后端，包含模型加载
- `calc_mcdm_pvpi.py` - PVPI计算核心逻辑
- `ThreeChinaMap.vue` - 3D地图组件
- `App.vue` - 主应用界面

### 添加新模型
1. 将模型文件放入 `models/models/` 目录
2. 在 `api_server_full.py` 中加载新模型
3. 更新前端预测接口调用

## 📝 注意事项

- 模型文件体积较大，使用Git LFS管理
- 地理数据需保持坐标系一致性
- 前端构建前需确保数据同步：`npm run sync:data`

## 👥 作者

**LinJJ12** - 项目主要开发者

## 📄 许可证

本项目仅供学习和研究使用。

---

**让清洁能源点亮未来！** 🌞
