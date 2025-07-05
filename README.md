# 微信小程序后端服务

这是一个为微信小程序提供后端API服务的Flask应用，主要功能包括：

## 功能特性

### 1. 实时天气服务
- 获取指定城市的实时天气信息
- 5天天气预报
- 空气质量数据
- 30天趋势预测
- 历史天气查询
- 天气地图图层支持

### 2. 热力图生成服务
- 支持Excel文件上传
- 多种插值方法（克里金插值等）
- 自定义地图图层
- 多种颜色主题
- 实时生成热力图

### 3. 地图数据服务
- 支持Excel文件上传
- 数据点可视化
- 会话管理

## API端点

### 天气相关
- `GET /api/weather/realtime/<city_name>` - 获取实时天气
- `GET /api/weather/history/<city_name>?date=YYYY-MM-DD` - 获取历史天气
- `GET /api/weather/trends/<city_name>` - 获取30天趋势
- `GET /api/weather/map_layers` - 获取地图图层
- `GET /api/weather/map_tile/<op>/<z>/<x>/<y>` - 地图瓦片代理

### 热力图相关
- `POST /api/heatmap/generate` - 生成热力图

### 地图相关
- `POST /map/upload` - 上传地图数据
- `GET /map/get-data` - 获取地图数据

## 部署到Render

### 1. 环境变量配置
在Render控制台中设置以下环境变量：
- `OPENWEATHER_API_KEY` - OpenWeatherMap API密钥

### 2. 部署步骤
1. 将代码推送到GitHub仓库
2. 在Render中创建新的Web Service
3. 连接GitHub仓库
4. 设置构建命令：`pip install -r requirements.txt`
5. 设置启动命令：`gunicorn run:app`
6. 配置环境变量
7. 部署

### 3. 文件结构
```
hou_python/
├── app/
│   ├── __init__.py          # Flask应用工厂
│   ├── config.py            # 配置管理
│   ├── services/            # 业务逻辑服务
│   │   ├── weather_service.py
│   │   └── heatmap_service.py
│   ├── views/               # API路由
│   │   ├── weather_routes.py
│   │   ├── heatmap_routes.py
│   │   └── map_routes.py
│   └── shanxigeo/           # 地理数据
├── requirements.txt         # Python依赖
├── Procfile                # Render部署配置
└── run.py                  # 应用入口
```

## 本地开发

1. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 设置环境变量：
```bash
# 创建.env文件
echo "OPENWEATHER_API_KEY=your_api_key_here" > .env
```

4. 运行应用：
```bash
python run.py
```

## 注意事项

- 确保OpenWeatherMap API密钥有效
- 热力图生成需要足够的内存资源
- 地图数据文件应包含必要的列：经度、纬度、污染物浓度、标记名称 