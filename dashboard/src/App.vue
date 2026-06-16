<template>
  <div class="screen" :class="{ 'data-load-error': dataLoadError }">
    <header class="screen-header">
      <div class="brand">
        <span class="brand-mark"></span>
        <h1>光伏电站智能选址数据可视化大屏</h1>
      </div>
      <nav class="tabs" aria-label="数据视图">
        <button class="tab" :class="{ active: activeTab === 'dashboard' }" @click="activeTab = 'dashboard'">选址态势</button>
        <button class="tab" :class="{ active: activeTab === 'resourceProfit' }" @click="activeTab = 'resourceProfit'">资源收益评估</button>
        <button class="tab" :class="{ active: activeTab === 'realtime' }" @click="activeTab = 'realtime'">实时选址</button>
      </nav>
      <div class="timebox">
        <strong>{{ currentTime }}</strong>
        <span>{{ currentDate }}</span>
      </div>
    </header>

    <main class="dashboard" v-if="activeTab === 'dashboard'">
      <section class="side left-stack dashboard-left">
        <article class="panel stats-panel">
          <div class="panel-title"><span></span>全国光伏样本站统计<em>单位：座 / km2</em></div>
          <div class="stats-panel-body">
            <div class="metric-grid">
              <div class="metric" v-for="item in metrics" :key="item.label">
                <div class="metric-icon">{{ item.icon }}</div>
                <div class="metric-content">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}<small>{{ item.unit }}</small></strong>
                </div>
              </div>
            </div>
          </div>
        </article>

        <article class="panel suitability-panel">
          <div class="panel-title"><span></span>各等级选址占比<em>单位：%</em></div>
          <div class="suitability-panel-body">
            <div ref="suitabilityPieRef" class="suitability-chart"></div>
            <div class="progress-list">
              <div class="progress-item" v-for="grade in suitability" :key="grade.name">
                <span>{{ grade.name }}</span>
                <i><b :style="{ width: `${grade.value}%`, background: grade.color }"></b></i>
                <strong>{{ grade.count }}</strong>
              </div>
            </div>
          </div>
        </article>
      </section>

      <section class="center-stage dashboard-map-stage">
        <div class="map-shell">
          <ThreeChinaMap
            v-if="chinaGeoJson"
            class="map-chart"
            :geo-json="chinaGeoJson"
            :stats="statsData"
            :stations="stationData"
            :province-names="provinceNames"
            :normalize-province-name="normalizeProvinceName"
            mode="dashboard"
            @province-focus="handleProvinceFocus"
            @map-pick="handleThreeMapPick"
          />
          <div class="map-summary">
            <span>PVPI 均值</span>
            <strong>{{ summary.avgPvpi }}</strong>
            <span>最大辐照</span>
            <strong>{{ summary.maxGhi }} kWh/m2</strong>
          </div>
        </div>
      </section>

      <section class="side right-stack dashboard-right">
        <article class="panel hex-panel">
          <div class="panel-title"><span></span>高潜力省份梯队<em>站点 / 面积</em></div>
          <div class="scrollable-panel" style="height: calc(100% - 26px);">
            <div class="hex-grid">
              <div class="hex" v-for="province in provinceLeaders" :key="province.name">
                <strong>{{ province.score }}</strong>
                <span>{{ province.name }}</span>
                <small>{{ province.area }} km2</small>
              </div>
            </div>
          </div>
        </article>

        <article class="panel chart-panel split-panel">
          <div class="panel-title"><span></span>资源与风险画像<em>标准化</em></div>
          <div ref="radarChartRef" class="chart half"></div>
          <div class="risk-list">
            <div><span>可建设面积</span><strong>{{ summary.totalArea }} km2</strong></div>
            <div><span>候选站点</span><strong>{{ summary.totalStations }} 座</strong></div>
          </div>
        </article>
      </section>
    </main>

    <main class="resource-profit-dashboard" v-else-if="activeTab === 'resourceProfit'">
      <article class="panel chart-panel">
        <div class="panel-title"><span></span>省域平均潜力趋势<em>折线 / PVPI</em></div>
        <div ref="trendChartRef" class="chart"></div>
      </article>

      <article class="panel chart-panel">
        <div class="panel-title"><span></span>省域装机潜力排行<em>柱状 / km2</em></div>
        <div ref="barChartRef" class="chart"></div>
      </article>

      <article class="panel chart-panel">
        <div class="panel-title"><span></span>资源收益散点<em>GHI × PVPI</em></div>
        <div ref="scatterChartRef" class="chart"></div>
      </article>

      <article class="panel chart-panel">
        <div class="panel-title"><span></span>等级结构占比<em>饼图 / %</em></div>
        <div ref="pieChartRef" class="chart"></div>
      </article>

      <article class="panel chart-panel">
        <div class="panel-title"><span></span>省域收益波动<em>K线 / PVPI 分布</em></div>
        <div ref="klineChartRef" class="chart"></div>
      </article>

      <article class="panel table-panel">
        <div class="panel-title"><span></span>综合评分 TOP10 候选电站<em>真实样本</em></div>
        <div class="scrollable-panel" style="height: calc(100% - 34px);">
          <table>
            <thead>
              <tr><th>序号</th><th>省份</th><th>面积 km2</th><th>GHI</th><th>降水 mm</th><th>PVPI</th></tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in topSites" :key="row.index">
                <td>{{ index + 1 }}</td><td>{{ row.provinceName }}</td><td>{{ row.area_km2 }}</td><td>{{ row.ghi_mean }}</td><td>{{ row.precip_annual }}</td><td>{{ row.PVPI }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </main>

    <main class="realtime-dashboard" v-else-if="activeTab === 'realtime'">
      <section class="realtime-map-section">
        <div class="realtime-map-shell">
          <ThreeChinaMap
            v-if="chinaGeoJson"
            class="realtime-map-chart"
            :geo-json="chinaGeoJson"
            :stats="statsData"
            :stations="stationData"
            :province-names="provinceNames"
            :normalize-province-name="normalizeProvinceName"
            :result-point="lastClickLatLng"
            mode="realtime"
            @province-focus="handleProvinceFocus"
            @map-pick="handleThreeMapPick"
          />
          <div class="map-hint">
            <span class="hint-icon">+</span>
            <span>点击省份聚焦，点击地图表面进行实时选址分析</span>
          </div>
        </div>
      </section>

      <section class="realtime-result-section">
        <article class="panel model-toggle-panel">
          <div class="panel-title"><span></span>预测模型选择</div>
          <div class="toggle-content">
            <div class="model-status">
              <span class="status-label">当前模型：</span>
              <strong class="status-value" :class="{ 'full-model': useFullModel }">{{ modelStatusText }}</strong>
            </div>
            <div class="toggle-buttons">
              <button class="toggle-btn" :class="{ active: !useFullModel }" @click="toggleModel('simple')">简化公式</button>
              <button class="toggle-btn full-btn" :class="{ active: useFullModel }" @click="toggleModel('full')">GAT+GBDT</button>
            </div>
            <div class="model-hint">
              <span v-if="useFullModel">完整模型：使用图神经网络和梯度提升树进行预测；失败时自动回退</span>
              <span v-else>简化公式：基于真实太阳能数据快速估算</span>
            </div>
          </div>
        </article>

        <article class="panel result-panel analysis-panel">
          <div class="panel-title">
            <span></span>{{ realtimeResult ? "选址分析结果" : isLoading ? "正在分析..." : errorMessage ? "分析状态" : "实时选址分析" }}
            <em v-if="realtimeResult" class="model-tag" :class="{ 'full-model': realtimeResult.model_type !== '简化公式' }">{{ realtimeResult.model_type }}</em>
          </div>
          <div class="loading-content" v-if="isLoading">
            <div class="loading-spinner"></div>
            <p>正在从 NASA POWER 获取点击位置气候数据...</p>
            <p>正在运行 GAT+GBDT 模型计算 PVPI...</p>
            <p class="loading-hint">首次请求可能需要 30-90 秒，请耐心等待</p>
          </div>

          <div class="error-content" v-else-if="errorMessage">
            <div class="error-icon">×</div>
            <p>{{ errorMessage }}</p>
            <button class="retry-btn" @click="retryAnalysis">重试</button>
          </div>

          <div class="result-content" v-else-if="realtimeResult">
            <div class="result-hero" :style="{ '--score-color': realtimeResult.level_color }">
              <div class="score-ring"><b>{{ realtimeResult.pvpi.toFixed(2) }}</b><small>PVPI</small></div>
              <div class="result-hero-meta">
                <div class="level-badge" :style="{ background: realtimeResult.level_color }">{{ realtimeResult.level }}</div>
                <div class="suitability-text"><span>适配度</span><strong :style="{ color: realtimeResult.level_color }">{{ realtimeResult.suitability }}</strong></div>
              </div>
            </div>

            <div class="compact-data-grid">
              <div class="data-card"><span class="data-label">经度</span><strong>{{ realtimeResult.lon.toFixed(4) }}°</strong></div>
              <div class="data-card"><span class="data-label">纬度</span><strong>{{ realtimeResult.lat.toFixed(4) }}°</strong></div>
              <div class="data-card"><span class="data-label">年均太阳辐射</span><strong>{{ realtimeResult.solar_data.ghi_annual_mean }} kWh/m2</strong></div>
              <div class="data-card"><span class="data-label">辐射标准差</span><strong>{{ realtimeResult.solar_data.ghi_annual_std }} kWh/m2</strong></div>
              <div class="data-card"><span class="data-label">年均温度</span><strong>{{ realtimeResult.solar_data.temp_annual_mean }} °C</strong></div>
              <div class="data-card"><span class="data-label">年降水量</span><strong>{{ realtimeResult.solar_data.precip_annual_mean }} mm</strong></div>
            </div>
            <div class="data-card source-card" v-if="realtimeResult.solar_data.source"><span class="data-label">数据来源</span><strong>{{ realtimeResult.solar_data.source }}</strong></div>
            <div class="data-card source-card" v-if="realtimeResult.inference_version"><span class="data-label">推理版本</span><strong>{{ realtimeResult.inference_version }}</strong></div>
            <div class="data-card source-card" v-if="realtimeResult.fallback_reason"><span class="data-label">回退原因</span><strong>{{ realtimeResult.fallback_reason }}</strong></div>
          </div>

          <div class="empty-content" v-else>
            <div class="empty-icon">+</div>
            <p>请在左侧地图上点击任意位置</p>
            <p>系统将获取真实太阳能数据</p>
            <p>并进行光伏电站选址适配度评估</p>
            <div class="mouse-coords" v-if="mouseCoords">
              <div class="coord-item"><span>经度</span><strong>{{ mouseCoords.lon.toFixed(4) }}°</strong></div>
              <div class="coord-item"><span>纬度</span><strong>{{ mouseCoords.lat.toFixed(4) }}°</strong></div>
            </div>
          </div>
        </article>
      </section>
    </main>
  </div>
</template>
<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import ThreeChinaMap from "./components/ThreeChinaMap.vue";

const activeTab = ref("dashboard");
const realtimeResult = ref(null);
const isLoading = ref(false);
const errorMessage = ref("");
const lastClickLatLng = ref(null);
const mouseCoords = ref(null);
const useFullModel = ref(false);
const modelStatusText = ref("简化公式");

const provinceNames = {
  anhui: "安徽",
  beijing: "北京",
  chongqing: "重庆",
  fujian: "福建",
  gansu: "甘肃",
  guangdong: "广东",
  guangxi: "广西",
  guizhou: "贵州",
  hainan: "海南",
  hebei: "河北",
  heilongjiang: "黑龙江",
  henan: "河南",
  hong_kong: "香港",
  hubei: "湖北",
  hunan: "湖南",
  Inner_Mongolia: "内蒙古",
  jiangsu: "江苏",
  jiangxi: "江西",
  jilin: "吉林",
  liaoning: "辽宁",
  macao: "澳门",
  ningxia: "宁夏",
  qinghai: "青海",
  shaanxi: "陕西",
  shandong: "山东",
  shanghai: "上海",
  shanxi: "山西",
  sichuan: "四川",
  taiwan: "台湾",
  tianjin: "天津",
  xinjiang: "新疆",
  xizang: "西藏",
  yunnan: "云南",
  zhejiang: "浙江"
};

const normalizeProvinceName = (name = "") =>
  String(name)
    .replace("新疆维吾尔自治区", "新疆")
    .replace("广西壮族自治区", "广西")
    .replace("宁夏回族自治区", "宁夏")
    .replace("西藏自治区", "西藏")
    .replace("内蒙古自治区", "内蒙古")
    .replace("香港特别行政区", "香港")
    .replace("澳门特别行政区", "澳门")
    .replace(/[省市]/g, "");

const currentTime = ref("--:--:--");
const currentDate = ref("");
const metrics = ref([]);
const suitability = ref([]);
const topSites = ref([]);
const provinceLeaders = ref([]);
const resourceRows = ref([]);
const profitRows = ref([]);
const dataLoadError = ref("");
const summary = ref({
  avgPvpi: "--",
  maxGhi: "--",
  totalArea: "--",
  totalStations: "--"
});
const statsData = ref([]);
const stationData = ref([]);
const chinaGeoJson = ref(null);

const trendChartRef = ref(null);
const radarChartRef = ref(null);
const barChartRef = ref(null);
const suitabilityPieRef = ref(null);
const scatterChartRef = ref(null);
const pieChartRef = ref(null);
const klineChartRef = ref(null);
const charts = [];
let clockTimer;

const chartTheme = {
  textStyle: { color: "#b9d8df" },
  grid: { left: 42, right: 20, top: 28, bottom: 30 },
  tooltip: {
    trigger: "axis",
    backgroundColor: "rgba(2, 14, 22, .96)",
    borderColor: "rgba(68, 231, 248, .6)",
    borderWidth: 1,
    extraCssText: "box-shadow:0 0 18px rgba(39,231,243,.22);backdrop-filter:blur(6px);",
    textStyle: { color: "#e8fbff" }
  },
  xAxis: {
    axisLine: { lineStyle: { color: "rgba(142, 181, 192, .42)" } },
    axisTick: { show: false },
    axisLabel: { color: "#a8cbd2" }
  },
  yAxis: {
    splitLine: { lineStyle: { color: "rgba(68, 231, 248, .13)", type: "dashed" } },
    axisLabel: { color: "#a8cbd2" }
  }
};

let chinaMapPromise = null;

const loadChinaMap = async () => {
  if (!chinaMapPromise) {
    chinaMapPromise = (async () => {
      const urls = ["/data/china_full.json", "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"];
      let lastError;
      for (const url of urls) {
        try {
          const response = await fetch(url);
          if (!response.ok) throw new Error(`${url} load failed`);
          const geoJson = await response.json();
          chinaGeoJson.value = geoJson;
          return geoJson;
        } catch (error) {
          lastError = error;
        }
      }
      throw lastError || new Error("china map load failed");
    })();
  }
  return chinaMapPromise;
};

const visibleCharts = computed(() => charts.filter(Boolean));

const formatNumber = (value, digits = 0) =>
  Number(value || 0).toLocaleString("zh-CN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  });

const normalizeSolarData = (row, source) => ({
  ghi_annual_mean: Number(row.ghi_mean || row.ghi_annual_mean || 0),
  ghi_annual_std: Number(row.ghi_std || row.ghi_annual_std || 0),
  temp_annual_mean: Number(row.temp_mean || row.temp_annual_mean || 0),
  temp_annual_std: Number(row.temp_std || row.temp_annual_std || 0),
  precip_annual_mean: Number(row.precip_annual || row.precip_annual_mean || 0),
  source
});

const calculateSimplePvpi = (solarData) => {
  const ghi = Number(solarData.ghi_annual_mean || 0);
  const temp = Number(solarData.temp_annual_mean || 0);
  const tempStd = Number(solarData.temp_annual_std || 0);
  const precip = Number(solarData.precip_annual_mean || 0);
  const ghiScore = Math.min(ghi / 6, 1);
  const tempScore = Math.min(Math.max((25 - Math.abs(temp - 15)) / 25, 0), 1);
  const precipScore = Math.min(Math.max((1000 - precip) / 1000, 0), 1);
  const stabilityScore = Math.min(Math.max((10 - tempStd) / 10, 0), 1);
  return Math.max(0.1, Math.min(0.95, Number((0.3 * ghiScore + 0.2 * tempScore + 0.25 * precipScore + 0.25 * stabilityScore).toFixed(4))));
};

const classifyPvpi = (pvpi) => {
  if (pvpi >= 0.8) return { level: "优选区", level_color: "#00ff88", suitability: "极高" };
  if (pvpi >= 0.6) return { level: "适宜区", level_color: "#27e7f3", suitability: "高" };
  if (pvpi >= 0.4) return { level: "备选区", level_color: "#f3df54", suitability: "中等" };
  return { level: "约束区", level_color: "#ff6b6b", suitability: "低" };
};

const buildLocalPrediction = (lat, lon, reason = "") => {
  if (!stationData.value.length) {
    throw new Error("本地真实电站数据尚未加载");
  }
  const nearest = stationData.value.reduce((best, row) => {
    const distance = Math.hypot(Number(row.lon) - lon, Number(row.lat) - lat);
    return !best || distance < best.distance ? { row, distance } : best;
  }, null);
  const solarData = normalizeSolarData(
    nearest.row,
    `nearest real station: ${provinceNames[nearest.row.province] || nearest.row.province} #${nearest.row.index}`
  );
  const pvpi = calculateSimplePvpi(solarData);
  const classification = classifyPvpi(pvpi);
  return {
    lat,
    lon,
    pvpi,
    pvssi: pvpi,
    ...classification,
    model_type: "简化公式（本地真实数据兜底）",
    fallback_reason: reason,
    solar_data: {
      ghi_annual_mean: Number(solarData.ghi_annual_mean.toFixed(2)),
      ghi_annual_std: Number(solarData.ghi_annual_std.toFixed(2)),
      temp_annual_mean: Number(solarData.temp_annual_mean.toFixed(2)),
      temp_annual_std: Number(solarData.temp_annual_std.toFixed(2)),
      precip_annual_mean: Number(Math.max(0, solarData.precip_annual_mean).toFixed(2)),
      source: solarData.source
    }
  };
};

const parseCsv = (text) => {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines.shift().split(",");
  return lines.map((line) => {
    const cols = line.split(",");
    return headers.reduce((row, key, index) => {
      const value = cols[index];
      const numeric = Number(value);
      row[key] = Number.isFinite(numeric) && value !== "" ? numeric : value;
      return row;
    }, {});
  });
};

const tick = () => {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString("zh-CN", { hour12: false });
  currentDate.value = now.toLocaleDateString("zh-CN", {
    weekday: "short",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
};

const loadData = async () => {
  dataLoadError.value = "";

  try {
    const [statsText, stationText] = await Promise.all([
      fetch("/data/provincial_statistics.csv").then((res) => {
        if (!res.ok) throw new Error("provincial_statistics.csv load failed");
        return res.text();
      }),
      fetch("/data/pv_stations_mcdm_scored.csv").then((res) => {
        if (!res.ok) throw new Error("pv_stations_mcdm_scored.csv load failed");
        return res.text();
      })
    ]);
    const stats = parseCsv(statsText);
    const stations = parseCsv(stationText);
    validateData(stats, stations);
    statsData.value = stats;
    stationData.value = stations;
    prepareCards(stats, stations);
    await nextTick();
    renderActiveCharts();
  } catch (error) {
    dataLoadError.value = error.message || "真实数据加载失败";
    metrics.value = [];
    suitability.value = [];
    topSites.value = [];
    provinceLeaders.value = [];
    resourceRows.value = [];
    profitRows.value = [];
    summary.value = {
      avgPvpi: "--",
      maxGhi: "--",
      totalArea: "--",
      totalStations: "--"
    };
    statsData.value = [];
    stationData.value = [];
    visibleCharts.value.forEach((chart) => chart.dispose());
    charts.length = 0;
    throw error;
  }
};

const validateData = (stats, stations) => {
  if (!stats.length || !stations.length) {
    throw new Error("真实数据文件为空");
  }
  const requiredStats = ["province", "Count", "Total_Area_km2"];
  const requiredStations = ["province", "lon", "lat", "area_km2", "ghi_mean", "temp_mean", "temp_std", "precip_annual", "PVPI"];
  for (const field of requiredStats) {
    if (!(field in stats[0])) throw new Error(`省级统计缺少字段: ${field}`);
  }
  for (const field of requiredStations) {
    if (!(field in stations[0])) throw new Error(`站点数据缺少字段: ${field}`);
  }
};

const prepareCards = (stats, stations) => {
  const totalStations = stats.reduce((sum, row) => sum + row.Count, 0);
  const totalArea = stats.reduce((sum, row) => sum + row.Total_Area_km2, 0);
  const avgPvpi = stations.reduce((sum, row) => sum + row.PVPI, 0) / stations.length;
  const maxGhi = Math.max(...stations.map((row) => row.ghi_mean));
  const avgTemp = stations.reduce((sum, row) => sum + row.temp_mean, 0) / stations.length;

  summary.value = {
    avgPvpi: formatNumber(avgPvpi, 2),
    maxGhi: formatNumber(maxGhi, 2),
    totalArea: formatNumber(totalArea, 1),
    totalStations: formatNumber(totalStations)
  };

  metrics.value = [
    { label: "候选电站", value: formatNumber(totalStations), unit: "座", icon: "站" },
    { label: "覆盖省域", value: formatNumber(stats.length), unit: "个", icon: "省" },
    { label: "可用面积", value: formatNumber(totalArea, 1), unit: "km2", icon: "面" },
    { label: "平均温度", value: formatNumber(avgTemp, 1), unit: "°C", icon: "温" }
  ];

  const sortedPvpi = [...stations].sort((a, b) => b.PVPI - a.PVPI);
  const thresholds = [
    sortedPvpi[Math.floor(sortedPvpi.length * 0.15)].PVPI,
    sortedPvpi[Math.floor(sortedPvpi.length * 0.4)].PVPI,
    sortedPvpi[Math.floor(sortedPvpi.length * 0.7)].PVPI
  ];
  const counts = [
    stations.filter((row) => row.PVPI >= thresholds[0]).length,
    stations.filter((row) => row.PVPI < thresholds[0] && row.PVPI >= thresholds[1]).length,
    stations.filter((row) => row.PVPI < thresholds[1] && row.PVPI >= thresholds[2]).length,
    stations.filter((row) => row.PVPI < thresholds[2]).length
  ];
  suitability.value = [
    { name: "优选区", value: Math.round((counts[0] / stations.length) * 100), count: formatNumber(counts[0]), color: "#27e7f3" },
    { name: "适宜区", value: Math.round((counts[1] / stations.length) * 100), count: formatNumber(counts[1]), color: "#35f0a2" },
    { name: "备选区", value: Math.round((counts[2] / stations.length) * 100), count: formatNumber(counts[2]), color: "#f3df54" },
    { name: "约束区", value: Math.round((counts[3] / stations.length) * 100), count: formatNumber(counts[3]), color: "#ff8b38" }
  ];

  topSites.value = sortedPvpi.slice(0, 10).map((row) => ({
    ...row,
    provinceName: provinceNames[row.province] || row.province,
    area_km2: formatNumber(row.area_km2, 2),
    ghi_mean: formatNumber(row.ghi_mean, 2),
    precip_annual: formatNumber(row.precip_annual, 0),
    PVPI: formatNumber(row.PVPI, 2)
  }));

  provinceLeaders.value = [...stats]
    .sort((a, b) => b.Total_Area_km2 - a.Total_Area_km2)
    .slice(0, 6)
    .map((row) => ({
      name: provinceNames[row.province] || row.province,
      score: formatNumber(row.Count),
      area: formatNumber(row.Total_Area_km2, 0)
    }));

  const stationGroups = stations.reduce((groups, row) => {
    if (!groups.has(row.province)) groups.set(row.province, []);
    groups.get(row.province).push(row);
    return groups;
  }, new Map());

  const provinceSummary = stats.map((row) => {
    const rows = stationGroups.get(row.province) || [];
    const avgValue = (key) => rows.reduce((sum, item) => sum + item[key], 0) / rows.length;
    const avgPvpi = avgValue("PVPI");
    const avgGhi = avgValue("ghi_mean");
    return {
      province: row.province,
      provinceName: provinceNames[row.province] || row.province,
      count: row.Count,
      totalArea: row.Total_Area_km2,
      avgPvpi,
      avgGhi,
      profitIndex: avgPvpi * row.Total_Area_km2
    };
  }).filter((row) => Number.isFinite(row.avgPvpi) && Number.isFinite(row.avgGhi));

  resourceRows.value = [...provinceSummary]
    .sort((a, b) => b.avgGhi - a.avgGhi)
    .slice(0, 10)
    .map((row) => ({
      ...row,
      count: formatNumber(row.count),
      totalArea: formatNumber(row.totalArea, 1),
      avgPvpi: formatNumber(row.avgPvpi, 2),
      avgGhi: formatNumber(row.avgGhi, 2)
    }));

  profitRows.value = [...provinceSummary]
    .sort((a, b) => b.profitIndex - a.profitIndex)
    .slice(0, 10)
    .map((row) => ({
      ...row,
      count: formatNumber(row.count),
      totalArea: formatNumber(row.totalArea, 1),
      avgPvpi: formatNumber(row.avgPvpi, 2),
      profitIndex: formatNumber(row.profitIndex, 0)
    }));
};

const initChart = (chartRef) => {
  const chart = echarts.init(chartRef.value);
  charts.push(chart);
  return chart;
};

const renderCharts = (stats, stations) => {
  visibleCharts.value.forEach((chart) => chart.dispose());
  charts.length = 0;
  renderRadar(stats, stations);
};

const renderActiveCharts = () => {
  const stats = statsData.value;
  const stations = stationData.value;
  if (!stats.length || !stations.length) return;

  visibleCharts.value.forEach((chart) => chart.dispose());
  charts.length = 0;

  if (activeTab.value === "dashboard") {
    renderDashboardSuitabilityPie();
    renderRadar(stats, stations);
  } else if (activeTab.value === "resourceProfit") {
    renderProvincePvpi(stats, stations);
    renderBar(stats);
    renderResourceScatter(stats, stations);
    renderSuitabilityPie();
    renderProvinceKline(stats, stations);
  }
};

const renderProvincePvpi = (stats, stations) => {
  const stationGroups = stations.reduce((groups, row) => {
    if (!groups.has(row.province)) groups.set(row.province, []);
    groups.get(row.province).push(row);
    return groups;
  }, new Map());
  const provincePvpi = [...stats]
    .map((row) => {
      const provinceStations = stationGroups.get(row.province) || [];
      const avgPvpi = provinceStations.reduce((sum, station) => sum + station.PVPI, 0) / provinceStations.length;
      return {
        province: provinceNames[row.province] || row.province,
        avgPvpi: Number(avgPvpi.toFixed(2))
      };
    })
    .filter((row) => Number.isFinite(row.avgPvpi))
    .sort((a, b) => b.avgPvpi - a.avgPvpi)
    .slice(0, 12)
    .reverse();
  const chart = initChart(trendChartRef);
  chart.setOption({
    ...chartTheme,
    xAxis: { ...chartTheme.xAxis, type: "category", data: provincePvpi.map((row) => row.province) },
    yAxis: { ...chartTheme.yAxis, type: "value" },
    series: [
      {
        type: "line",
        data: provincePvpi.map((row) => row.avgPvpi),
        symbol: "circle",
        symbolSize: 8,
        smooth: true,
        lineStyle: { color: "#27e7f3", width: 3, shadowBlur: 12, shadowColor: "rgba(39, 231, 243, .5)" },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(39, 231, 243, .34)" },
            { offset: 1, color: "rgba(39, 231, 243, .02)" }
          ])
        },
        itemStyle: {
          color: "#f3df54",
          borderColor: "#ffffff",
          borderWidth: 1,
          shadowBlur: 12,
          shadowColor: "rgba(243, 223, 84, .38)"
        },
        emphasis: { itemStyle: { shadowBlur: 18, shadowColor: "rgba(243, 223, 84, .35)" } }
      }
    ]
  });
};

const renderBar = (stats) => {
  const top = [...stats].sort((a, b) => b.Total_Area_km2 - a.Total_Area_km2).slice(0, 10).reverse();
  const chart = initChart(barChartRef);
  chart.setOption({
    ...chartTheme,
    grid: { left: 58, right: 24, top: 22, bottom: 26 },
    xAxis: { ...chartTheme.xAxis, type: "value" },
    yAxis: {
      ...chartTheme.yAxis,
      type: "category",
      data: top.map((row) => provinceNames[row.province] || row.province)
    },
    series: [
      {
        type: "bar",
        data: top.map((row) => row.Total_Area_km2),
        barWidth: 10,
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: "#0b4f78" },
            { offset: 0.68, color: "#27e7f3" },
            { offset: 1, color: "#f3df54" }
          ]),
          shadowBlur: 10,
          shadowColor: "rgba(39, 231, 243, .28)"
        },
        label: { show: true, position: "right", color: "#dffbff", fontSize: 11 }
      }
    ]
  });
};

const renderDashboardSuitabilityPie = () => {
  const chart = initChart(suitabilityPieRef);
  chart.setOption({
    tooltip: {
      ...chartTheme.tooltip,
      trigger: "item",
      formatter(params) {
        return `${params.name}<br/>站点数量：${formatNumber(params.value)} 座<br/>占比：${params.percent}%`;
      }
    },
    legend: {
      orient: "horizontal",
      bottom: 0,
      left: "center",
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 16,
      textStyle: { color: "#c3d9df", fontSize: 11 }
    },
    series: [
      {
        type: "pie",
        radius: ["50%", "76%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: false,
        label: { show: false },
        labelLine: { show: false },
        itemStyle: {
          borderColor: "rgba(3, 20, 29, .95)",
          borderWidth: 2,
          shadowBlur: 10,
          shadowColor: "rgba(39, 231, 243, .18)"
        },
        data: suitability.value.map((item) => ({
          name: item.name,
          value: Number(String(item.count).replace(/,/g, "")),
          itemStyle: { color: item.color }
        }))
      }
    ]
  });
};

const renderResourceScatter = (stats, stations) => {
  const stationGroups = stations.reduce((groups, row) => {
    if (!groups.has(row.province)) groups.set(row.province, []);
    groups.get(row.province).push(row);
    return groups;
  }, new Map());
  const data = stats
    .map((row) => {
      const rows = stationGroups.get(row.province) || [];
      if (!rows.length) return null;
      const avg = (key) => rows.reduce((sum, item) => sum + item[key], 0) / rows.length;
      return [
        Number(avg("ghi_mean").toFixed(2)),
        Number(avg("PVPI").toFixed(2)),
        row.Count,
        provinceNames[row.province] || row.province,
        Number(row.Total_Area_km2.toFixed(1))
      ];
    })
    .filter(Boolean);
  const chart = initChart(scatterChartRef);
  chart.setOption({
    ...chartTheme,
    grid: { left: 48, right: 26, top: 28, bottom: 34 },
    tooltip: {
      ...chartTheme.tooltip,
      formatter(params) {
        const value = params.value;
        return `${value[3]}<br/>平均 GHI：${value[0]}<br/>平均 PVPI：${value[1]}<br/>电站：${formatNumber(value[2])} 座<br/>面积：${value[4]} km2`;
      }
    },
    xAxis: { ...chartTheme.xAxis, type: "value", name: "GHI" },
    yAxis: { ...chartTheme.yAxis, type: "value", name: "PVPI" },
    series: [
      {
        type: "scatter",
        data,
        symbolSize: (value) => Math.max(8, Math.min(30, Math.sqrt(value[2]) * 1.2)),
        itemStyle: {
          color: "rgba(39, 231, 243, .72)",
          borderColor: "#f3df54",
          borderWidth: 1,
          shadowBlur: 12,
          shadowColor: "rgba(39, 231, 243, .42)"
        }
      }
    ]
  });
};

const renderSuitabilityPie = () => {
  const chart = initChart(pieChartRef);
  chart.setOption({
    tooltip: { ...chartTheme.tooltip, trigger: "item" },
    legend: {
      bottom: 8,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: "#a8cbd2", fontSize: 11 }
    },
    series: [
      {
        type: "pie",
        radius: ["48%", "72%"],
        center: ["50%", "46%"],
        avoidLabelOverlap: true,
        label: { color: "#dffbff", formatter: "{b}\n{d}%" },
        labelLine: { lineStyle: { color: "rgba(68, 231, 248, .45)" } },
        data: suitability.value.map((item) => ({
          name: item.name,
          value: Number(String(item.count).replace(/,/g, "")),
          itemStyle: { color: item.color }
        }))
      }
    ]
  });
};

const quantile = (values, q) => {
  const sorted = [...values].sort((a, b) => a - b);
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  return sorted[base + 1] === undefined ? sorted[base] : sorted[base] + rest * (sorted[base + 1] - sorted[base]);
};

const renderProvinceKline = (stats, stations) => {
  const stationGroups = stations.reduce((groups, row) => {
    if (!groups.has(row.province)) groups.set(row.province, []);
    groups.get(row.province).push(row);
    return groups;
  }, new Map());
  const rows = stats
    .map((row) => {
      const values = (stationGroups.get(row.province) || []).map((item) => item.PVPI).filter(Number.isFinite);
      if (values.length < 4) return null;
      return {
        province: provinceNames[row.province] || row.province,
        avg: values.reduce((sum, value) => sum + value, 0) / values.length,
        candle: [
          Number(quantile(values, 0.25).toFixed(2)),
          Number(quantile(values, 0.75).toFixed(2)),
          Number(Math.min(...values).toFixed(2)),
          Number(Math.max(...values).toFixed(2))
        ]
      };
    })
    .filter(Boolean)
    .sort((a, b) => b.avg - a.avg)
    .slice(0, 10)
    .reverse();
  const allValues = rows.flatMap((row) => row.candle);
  const yMin = Math.max(0, Math.floor(Math.min(...allValues) / 5) * 5);
  const yMax = Math.ceil(Math.max(...allValues) / 5) * 5;
  const chart = initChart(klineChartRef);
  chart.setOption({
    ...chartTheme,
    grid: { left: 42, right: 18, top: 26, bottom: 36 },
    tooltip: {
      ...chartTheme.tooltip,
      trigger: "axis",
      formatter(params) {
        const item = params[0];
        const value = item.value;
        return `${item.name}<br/>Q1：${value[1]}<br/>Q3：${value[2]}<br/>最低：${value[3]}<br/>最高：${value[4]}`;
      }
    },
    xAxis: { ...chartTheme.xAxis, type: "category", data: rows.map((row) => row.province) },
    yAxis: { ...chartTheme.yAxis, type: "value", min: yMin, max: yMax },
    series: [
      {
        type: "candlestick",
        data: rows.map((row) => row.candle),
        itemStyle: {
          color: "rgba(39, 231, 243, .72)",
          color0: "rgba(243, 223, 84, .72)",
          borderColor: "#27e7f3",
          borderColor0: "#f3df54"
        }
      }
    ]
  });
};

const renderRadar = (stats, stations) => {
  const avg = (key) => stations.reduce((sum, row) => sum + row[key], 0) / stations.length;
  const max = (key) => Math.max(...stations.map((row) => row[key]));
  const totalArea = stats.reduce((sum, row) => sum + row.Total_Area_km2, 0);
  const stationDensity = totalArea > 0 ? stations.length / totalArea : 0;
  const densityScore = Math.min(1, stationDensity / 3);
  const values = [
    avg("ghi_mean") / max("ghi_mean"),
    densityScore,
    avg("PVPI") / max("PVPI"),
    1 - avg("precip_annual") / max("precip_annual"),
    1 - avg("temp_std") / max("temp_std")
  ].map((value) => Number((Math.max(0, Math.min(1, value)) * 100).toFixed(1)));

  const chart = initChart(radarChartRef);
  chart.setOption({
    tooltip: chartTheme.tooltip,
    radar: {
      center: ["50%", "52%"],
      radius: "66%",
      splitNumber: 4,
      axisName: { color: "#d5f7fb" },
      splitLine: { lineStyle: { color: "rgba(68, 231, 248, .22)" } },
      splitArea: { areaStyle: { color: ["rgba(39,231,243,.04)", "rgba(39,231,243,.1)"] } },
      axisLine: { lineStyle: { color: "rgba(68, 231, 248, .28)" } },
      indicator: [
        { name: "辐照", max: 100 },
        { name: "密度", max: 100 },
        { name: "PVPI", max: 100 },
        { name: "少雨", max: 100 },
        { name: "稳定", max: 100 }
      ]
    },
    series: [
      {
        type: "radar",
        data: [{ value: values, name: "全国均值" }],
        symbol: "circle",
        symbolSize: 6,
        lineStyle: { color: "#27e7f3", width: 2, shadowBlur: 12, shadowColor: "rgba(39, 231, 243, .5)" },
        areaStyle: {
          color: new echarts.graphic.RadialGradient(0.5, 0.5, 0.8, [
            { offset: 0, color: "rgba(243, 223, 84, .26)" },
            { offset: 1, color: "rgba(39, 231, 243, .22)" }
          ])
        },
        itemStyle: { color: "#f3df54", borderColor: "#fff", borderWidth: 1 }
      }
    ]
  });
};

const handleResize = () => {
  visibleCharts.value.forEach((chart) => chart.resize());
};

const API_BASES = ["http://127.0.0.1:5000", "http://localhost:5000"];

const fetchFromApi = async (path, options = {}) => {
  let lastError = null;
  for (const base of API_BASES) {
    try {
      const response = await fetch(`${base}${path}`, options);
      if (!response.ok) {
        throw new Error(`接口响应异常：${response.status}`);
      }
      return response;
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("后端服务不可用");
};

const fetchPrediction = async (lat, lon) => {
  isLoading.value = true;
  errorMessage.value = "";
  realtimeResult.value = null;
  
  try {
    const mode = useFullModel.value ? "full" : "simple";
    const timeoutMs = useFullModel.value ? 120000 : 30000;
    let lastError = null;

    for (const base of API_BASES) {
      try {
        const response = await fetch(
          `${base}/api/predict?lat=${lat}&lon=${lon}&mode=${mode}`,
          { signal: AbortSignal.timeout(timeoutMs) }
        );
        let result = null;
        try {
          result = await response.json();
        } catch {
          result = null;
        }
        if (!response.ok || result?.error || !result) {
          throw new Error(result?.error || (result ? `接口响应异常：${response.status}` : "无法解析响应数据"));
        }
        const source = String(result?.solar_data?.source || "");
        if (useFullModel.value) {
          if (!source.includes("NASA")) {
            throw new Error("未获取到 NASA 气候数据，请检查网络后重试");
          }
          if (result.inference_version !== "v3-nasa-gat-reg") {
            throw new Error("后端推理版本过旧，请重启 api_server_full.py 后重试");
          }
          if (Number(result.pvpi) >= 0.999) {
            throw new Error("PVPI 结果异常（恒为 1.00），请确认已重启最新版 api_server_full.py");
          }
        }
        realtimeResult.value = result;
        updateMapMarker(lat, lon, result.pvpi);
        return;
      } catch (error) {
        lastError = error;
      }
    }

    if (useFullModel.value) {
      throw lastError || new Error("GAT+GBDT 后端不可用，请确认已启动 api_server_full.py");
    }

    const fallback = buildLocalPrediction(lat, lon, lastError?.message || "后端服务不可用");
    realtimeResult.value = fallback;
    updateMapMarker(lat, lon, fallback.pvpi);
    
  } catch (error) {
    errorMessage.value = error.message || "获取真实数据失败";
  } finally {
    isLoading.value = false;
  }
};

const toggleModel = async (mode) => {
  errorMessage.value = "";
  try {
    const response = await fetchFromApi("/api/toggle_mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode })
    });
    const result = await response.json();
    if (result.success) {
      useFullModel.value = mode === "full";
      modelStatusText.value = useFullModel.value ? "GAT+GBDT集成模型" : "简化公式";
    }
  } catch (error) {
    useFullModel.value = mode === "full";
    modelStatusText.value = useFullModel.value ? "GAT+GBDT集成模型" : "简化公式";
  }
  if (lastClickLatLng.value) {
    fetchPrediction(lastClickLatLng.value.lat, lastClickLatLng.value.lon);
  }
};

const checkModelStatus = async () => {
  try {
    const response = await fetchFromApi("/api/status");
    const result = await response.json();
    const modelLoaded = Boolean(result.model_loaded);
    useFullModel.value = modelLoaded;
    modelStatusText.value = modelLoaded ? "GAT+GBDT集成模型" : "简化公式";
  } catch (error) {
    useFullModel.value = false;
    modelStatusText.value = "简化公式";
  }
};

const updateMapMarker = (lat, lon, pvpi) => {
  void lat;
  void lon;
  void pvpi;
};

const handleProvinceFocus = ({ province }) => {
  mouseCoords.value = null;
  if (province) {
    errorMessage.value = "";
  }
};

const handleThreeMapPick = ({ lat, lon }) => {
  mouseCoords.value = { lon, lat };
  lastClickLatLng.value = { lat, lon };
  if (activeTab.value === "realtime") {
    fetchPrediction(lat, lon);
  }
};

const retryAnalysis = () => {
  if (lastClickLatLng.value) {
    fetchPrediction(lastClickLatLng.value.lat, lastClickLatLng.value.lon);
  }
};

const handleRealtimeResize = () => {
  return;
};

watch(activeTab, async (newTab) => {
  if (newTab === "realtime") {
    await nextTick();
    if (!statsData.value.length || !stationData.value.length) {
      await loadData();
    }
    checkModelStatus();
  } else {
    await nextTick();
    if (!statsData.value.length || !stationData.value.length) {
      await loadData();
    } else {
      renderActiveCharts();
    }
  }
});

onMounted(async () => {
  tick();
  clockTimer = window.setInterval(tick, 1000);
  await loadChinaMap();
  await loadData();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.clearInterval(clockTimer);
  window.removeEventListener("resize", handleResize);
  visibleCharts.value.forEach((chart) => chart.dispose());
});
</script>

