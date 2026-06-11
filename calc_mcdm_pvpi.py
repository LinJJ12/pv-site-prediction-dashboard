import pandas as pd
import numpy as np
from scipy.spatial import cKDTree

def calculate_pvpi(data_path, output_path):
    print("1. 加载光伏电站气象和地理数据...")
    df = pd.read_csv(data_path)
    
    # 构造评价指标
    # X1: 太阳辐射强度 (+)  ghi_mean
    # X2: 产业集聚效应与空间邻近性 (+)  50公里(约0.5度)范围内的电站数量
    coords = np.column_stack([df['lon'].values, df['lat'].values])
    tree = cKDTree(coords)
    # 计算每个站点0.5度半径内的邻居数量（作为产业集聚和空间连片度的代理）
    df['agglomeration'] = [len(inds) for inds in tree.query_ball_point(coords, r=0.5)]
    
    # X3: 辐射-温度-降水交互项 (+) 
    # 物理意义：在同等直射下，降水越少且偏离25度越小，有效转化率越高
    # 公式：GHI * exp(-降水/2000) * (1 - 0.004 * |T - 25|)
    temp_penalty = 1 - 0.004 * (df['temp_mean'] - 25).abs()
    precip_penalty = np.exp(-df['precip_annual'] / 2000.0)
    df['climate_interact'] = df['ghi_mean'] * precip_penalty * temp_penalty
    
    metrics = ['ghi_mean', 'agglomeration', 'climate_interact']
    directions = [1, 1, 1]
    
    print("2. 数据极差标准化 (Min-Max Normalization)...")
    Y = pd.DataFrame()
    for m, d in zip(metrics, directions):
        min_val = df[m].min()
        max_val = df[m].max()
        if max_val == min_val:
            Y[m] = 0
            continue
            
        if d == 1:
            Y[m] = (df[m] - min_val) / (max_val - min_val)
        else:
            Y[m] = (max_val - df[m]) / (max_val - min_val)
            
    print("3. AHP主观赋权 (基于九标度判断矩阵)...")
    # AHP专家打分：交互项(实际效能) 与 绝对辐射并重，产业聚集(空间邻近)作为重要加分项
    # 排列: 1. ghi_mean, 2. agglomeration, 3. climate_interact
    A = np.array([
        [1,   3,   1],
        [1/3, 1,   1/3],
        [1,   3,   1]
    ])
    
    # 求解最大特征值和对应的特征向量
    eigenvals, eigenvecs = np.linalg.eig(A)
    max_idx = np.argmax(np.real(eigenvals))
    w_ahp = np.real(eigenvecs[:, max_idx])
    w_ahp = w_ahp / np.sum(w_ahp) # 归一化
    
    print("4. 熵权法(EWM)客观赋权 (基于数据变异情况)...")
    # 平移避开ln(0)
    Y_shift = Y + 0.0001
    n = len(df)
    
    # 计算比重 P_ij
    P = Y_shift.div(Y_shift.sum(axis=0), axis=1)
    
    # 计算熵值 E_j 和差异系数 D_j
    E = - (1 / np.log(n)) * (P * np.log(P)).sum(axis=0)
    D = 1 - E
    w_ewm = D / D.sum() # 客观权重归一化
    
    print("5. 乘法合成博弈论组合权重...")
    w_combined = (w_ahp * w_ewm) / np.sum(w_ahp * w_ewm)
    
    print("6. 计算最终的光伏潜力指数 (PVPI, 0-100分)...")
    df['PVPI'] = 100 * Y.dot(w_combined)
    df.to_csv(output_path, index=False)
    
    return w_ahp, w_ewm, w_combined, df

if __name__ == "__main__":
    input_csv = "solar_data_output/pv_stations_solar_data.csv"
    output_csv = "solar_data_output/pv_stations_mcdm_scored.csv"
    
    w_ahp, w_ewm, w_combined, df_scored = calculate_pvpi(input_csv, output_csv)
    
    metrics_desc = ['ghi_mean (+ 辐射)', 'agglomeration (+ 集群)', 'climate_interact (+ 交互)']
    print("\n====== 权重计算结果 (AHP-EWM) ======")
    for i, m in enumerate(metrics_desc):
        print(f"{m:20s} -> AHP主观: {w_ahp[i]:.3f} | 熵权客观: {w_ewm[i]:.3f} | 最终组合: {w_combined[i]:.3f}")
        
    print("\n====== PVPI 光伏潜力最高的前 5 个站点 ======")
    top5 = df_scored[['province', 'lon', 'lat', 'ghi_mean', 'PVPI']].sort_values(by='PVPI', ascending=False).head(5)
    print(top5)
    
    print(f"\n✅ 评分完成！计算结果包含所有的 {len(df_scored)} 个站点。文件保存至: {output_csv}")
