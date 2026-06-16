"""
太阳辐射数据获取工具
使用NASA POWER API获取全球太阳辐射数据
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time

class SolarRadiationAPI:
    """NASA POWER API 封装类"""
    
    def __init__(self):
        self.base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        
    def get_solar_data(self, lat, lon, start_year=2020, end_year=2023):
        """
        获取指定位置的太阳辐射数据
        
        Parameters:
        -----------
        lat : float
            纬度
        lon : float
            经度
        start_year : int
            开始年份
        end_year : int
            结束年份
            
        Returns:
        --------
        dict : 包含GHI, DNI, 温度等指标的年均值
        """
        
        params = {
            'parameters': 'ALLSKY_SFC_SW_DWN,T2M,PRECTOTCORR',  # GHI, 温度, 降水
            'community': 'RE',
            'longitude': lon,
            'latitude': lat,
            'start': f'{start_year}0101',
            'end': f'{end_year}1231',
            'format': 'JSON'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # 提取参数
            properties = data['properties']['parameter']
            
            # 计算年均值
            ghi_values = list(properties['ALLSKY_SFC_SW_DWN'].values())
            temp_values = list(properties['T2M'].values())
            precip_values = list(properties['PRECTOTCORR'].values())
            
            # 过滤无效值
            ghi_values = [v for v in ghi_values if v != -999]
            temp_values = [v for v in temp_values if v != -999]
            precip_values = [v for v in precip_values if v != -999]
            
            # 计算年份数
            num_years = end_year - start_year + 1
            
            return {
                'ghi_annual_mean': np.mean(ghi_values),  # kWh/m²/day
                'ghi_annual_std': np.std(ghi_values),
                'temp_annual_mean': np.mean(temp_values),  # °C
                'temp_annual_std': np.std(temp_values),
                'precip_annual_mean': np.sum(precip_values) / num_years,  # mm/year (年均值)
            }
            
        except Exception as e:
            print(f"API请求失败 ({lat}, {lon}): {e}")
            return None
    
    def batch_get_solar_data(self, coordinates, delay=0.5):
        """
        批量获取多个位置的太阳辐射数据
        
        Parameters:
        -----------
        coordinates : list of tuples
            [(lat1, lon1), (lat2, lon2), ...]
        delay : float
            请求间隔时间(秒)，避免API限流
            
        Returns:
        --------
        pd.DataFrame : 包含所有位置数据的DataFrame
        """
        
        results = []
        total = len(coordinates)
        
        print(f"开始获取 {total} 个位置的太阳辐射数据...")
        
        for i, (lat, lon) in enumerate(coordinates):
            print(f"进度: {i+1}/{total} ({(i+1)/total*100:.1f}%)", end='\r')
            
            data = self.get_solar_data(lat, lon)
            
            if data:
                data['lat'] = lat
                data['lon'] = lon
                results.append(data)
            
            # 避免API限流
            if i < total - 1:
                time.sleep(delay)
        
        print(f"\n✓ 完成! 成功获取 {len(results)}/{total} 个位置的数据")
        
        return pd.DataFrame(results)


# 使用示例
if __name__ == "__main__":
    
    # 初始化API
    api = SolarRadiationAPI()
    
    # 单个位置测试
    print("="*60)
    print("单点测试: 北京 (39.9°N, 116.4°E)")
    print("="*60)
    
    data = api.get_solar_data(lat=39.9, lon=116.4)
    
    if data:
        print(f"\n年均GHI: {data['ghi_annual_mean']:.2f} kWh/m²/day")
        print(f"年均温度: {data['temp_annual_mean']:.2f} °C")
        print(f"年均降水量: {data['precip_annual_mean']:.2f} mm/year")
    
    # 批量测试 (示例: 3个城市)
    print("\n" + "="*60)
    print("批量测试: 3个城市")
    print("="*60)
    
    coords = [
        (39.9, 116.4),   # 北京
        (31.2, 121.5),   # 上海
        (23.1, 113.3),   # 广州
    ]
    
    df = api.batch_get_solar_data(coords, delay=1.0)
    
    print("\n结果预览:")
    print(df)
    
    # 保存结果
    df.to_csv('solar_radiation_sample.csv', index=False)
    print("\n✓ 结果已保存到: solar_radiation_sample.csv")
