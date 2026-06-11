"""
批量获取CPVPD-2024数据集所有光伏电站的太阳辐射数据
支持断点续传、进度保存、错误处理
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import time
from datetime import datetime
from utils_solar_data import SolarRadiationAPI
import warnings
warnings.filterwarnings('ignore')

class SolarDataFetcher:
    """太阳辐射数据批量获取器"""
    
    def __init__(self, data_dir, output_dir='solar_data_output'):
        """
        初始化
        
        Parameters:
        -----------
        data_dir : str
            CPVPD-2024数据集目录
        output_dir : str
            输出目录
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 文件路径
        self.progress_file = self.output_dir / 'fetch_progress.pkl'
        self.output_csv = self.output_dir / 'pv_stations_solar_data.csv'
        self.output_pkl = self.output_dir / 'pv_stations_solar_data.pkl'
        self.log_file = self.output_dir / 'fetch_log.txt'
        
        # API
        self.api = SolarRadiationAPI()
        
        # 数据存储
        self.gdf = None
        self.results = []
        self.failed_indices = []
        self.start_index = 0
        
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    
    def load_data(self):
        """加载所有光伏电站数据"""
        self.log("="*70)
        self.log("开始加载CPVPD-2024数据集")
        self.log("="*70)
        
        shp_files = list(self.data_dir.glob("*.shp"))
        
        if not shp_files:
            raise FileNotFoundError(f"未在 {self.data_dir} 找到shapefile文件")
        
        self.log(f"找到 {len(shp_files)} 个省份shapefile")
        
        # 读取所有省份数据
        gdfs = []
        for shp_file in shp_files:
            try:
                gdf = gpd.read_file(shp_file, encoding='utf-8')
                gdf['province'] = shp_file.stem
                gdfs.append(gdf)
                self.log(f"  ✓ {shp_file.stem}: {len(gdf)} 个电站")
            except Exception as e:
                self.log(f"  ✗ {shp_file.name} 加载失败: {e}")
        
        # 合并并保留原始 CRS（若存在），并显式设置为 EPSG:4326 以保证一致性
        if len(gdfs) > 0 and getattr(gdfs[0], 'crs', None) is not None:
            self.gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)
        else:
            self.gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
        # 明确设为 WGS84 (EPSG:4326)，允许覆盖以防个别文件缺失或不一致的 crs
        try:
            self.gdf = self.gdf.set_crs("EPSG:4326", allow_override=True)
        except Exception:
            # 如果无法设置，则保留现有 crs
            pass

        # 计算中心点
        self.gdf['centroid'] = self.gdf.geometry.centroid
        self.gdf['lon'] = self.gdf.centroid.x
        self.gdf['lat'] = self.gdf.centroid.y

        # 使用中国 Albers 等面积投影计算面积（适用于全国统计）
        aea = "+proj=aea +lat_1=25 +lat_2=47 +lat_0=35 +lon_0=105 +datum=WGS84 +units=m +no_defs"
        gdf_projected = self.gdf.to_crs(aea)
        self.gdf['area_km2'] = gdf_projected.geometry.area / 1e6
        
        self.log(f"\n✓ 数据加载完成")
        self.log(f"  总电站数: {len(self.gdf)}")
        self.log(f"  覆盖省份: {self.gdf['province'].nunique()}")
        self.log(f"  总面积: {self.gdf['area_km2'].sum():.2f} km²")
        
        return self.gdf
    
    def load_progress(self):
        """加载进度"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'rb') as f:
                    progress = pickle.load(f)
                
                self.results = progress.get('results', [])
                self.failed_indices = progress.get('failed_indices', [])
                self.start_index = progress.get('next_index', 0)
                
                self.log(f"\n✓ 加载进度: 已完成 {len(self.results)}/{len(self.gdf)} 个电站")
                self.log(f"  失败: {len(self.failed_indices)} 个")
                self.log(f"  下次从索引 {self.start_index} 开始")
                
                return True
            except Exception as e:
                self.log(f"⚠️ 加载进度失败: {e}，将从头开始")
                return False
        else:
            self.log("\n📌 未发现进度文件，将从头开始")
            return False
    
    def save_progress(self, current_index):
        """保存进度"""
        progress = {
            'results': self.results,
            'failed_indices': self.failed_indices,
            'next_index': current_index + 1,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.progress_file, 'wb') as f:
            pickle.dump(progress, f)
    
    def fetch_all(self, delay=0.6, save_interval=50):
        """
        批量获取所有电站的太阳辐射数据
        
        Parameters:
        -----------
        delay : float
            请求间隔(秒)，建议0.5-1.0，避免API限流
        save_interval : int
            每N个电站保存一次进度
        """
        total = len(self.gdf)
        
        self.log("\n" + "="*70)
        self.log("开始批量获取太阳辐射数据")
        self.log("="*70)
        self.log(f"总数: {total} 个电站")
        self.log(f"从索引: {self.start_index} 开始")
        self.log(f"请求间隔: {delay} 秒")
        self.log(f"预计耗时: {(total - self.start_index) * delay / 3600:.1f} 小时")
        self.log(f"预计完成时间: {datetime.now()}")
        self.log("="*70 + "\n")
        
        start_time = time.time()
        
        for i in range(self.start_index, total):
            row = self.gdf.iloc[i]
            lat, lon = row['lat'], row['lon']
            
            # 尝试获取数据
            try:
                data = self.api.get_solar_data(lat, lon, start_year=2020, end_year=2023)
                
                if data:
                    # 成功获取
                    result = {
                        'index': i,
                        'province': row['province'],
                        'lon': lon,
                        'lat': lat,
                        'area_km2': row['area_km2'],
                        'ghi_mean': data['ghi_annual_mean'],
                        'ghi_std': data['ghi_annual_std'],
                        'temp_mean': data['temp_annual_mean'],
                        'temp_std': data['temp_annual_std'],
                        'precip_annual': data['precip_annual_mean'],  # 年均降水量
                    }
                    self.results.append(result)
                else:
                    # 获取失败
                    self.failed_indices.append(i)
                    self.log(f"  ⚠️ 索引 {i} 获取失败")
                
            except Exception as e:
                # 异常处理
                self.failed_indices.append(i)
                self.log(f"  ❌ 索引 {i} 异常: {e}")
            
            # 进度显示
            if (i + 1) % 10 == 0 or i == total - 1:
                elapsed = time.time() - start_time
                success_count = len(self.results)
                failed_count = len(self.failed_indices)
                progress_pct = (i + 1) / total * 100
                avg_time = elapsed / (i - self.start_index + 1)
                eta = avg_time * (total - i - 1) / 3600
                
                self.log(f"进度: {i+1}/{total} ({progress_pct:.1f}%) | "
                        f"成功: {success_count} | 失败: {failed_count} | "
                        f"耗时: {elapsed/60:.1f}分钟 | 预计剩余: {eta:.1f}小时")
            
            # 定期保存进度
            if (i + 1) % save_interval == 0:
                self.save_progress(i)
                self.log(f"  💾 进度已保存 (索引: {i})")
            
            # API限流延迟
            if i < total - 1:
                time.sleep(delay)
        
        # 最终保存
        self.save_progress(total - 1)
        
        total_time = time.time() - start_time
        self.log("\n" + "="*70)
        self.log("数据获取完成！")
        self.log("="*70)
        self.log(f"总耗时: {total_time/3600:.2f} 小时")
        self.log(f"成功: {len(self.results)}/{total} ({len(self.results)/total*100:.2f}%)")
        self.log(f"失败: {len(self.failed_indices)}")
        
    def save_results(self):
        """保存结果到文件"""
        self.log("\n" + "="*70)
        self.log("保存结果")
        self.log("="*70)
        
        # 转换为DataFrame
        df_results = pd.DataFrame(self.results)
        
        # 保存CSV
        df_results.to_csv(self.output_csv, index=False, encoding='utf-8-sig')
        self.log(f"✓ CSV已保存: {self.output_csv}")
        self.log(f"  包含 {len(df_results)} 条记录")
        
        # 保存PKL
        with open(self.output_pkl, 'wb') as f:
            pickle.dump(df_results, f)
        self.log(f"✓ PKL已保存: {self.output_pkl}")
        
        # 保存失败索引
        if self.failed_indices:
            failed_file = self.output_dir / 'failed_indices.txt'
            with open(failed_file, 'w') as f:
                for idx in self.failed_indices:
                    f.write(f"{idx}\n")
            self.log(f"✓ 失败索引已保存: {failed_file}")
        
        # 统计信息
        self.log("\n【数据统计】")
        self.log(f"  GHI 平均值: {df_results['ghi_mean'].mean():.2f} kWh/m²/day")
        self.log(f"  GHI 范围: {df_results['ghi_mean'].min():.2f} - {df_results['ghi_mean'].max():.2f}")
        self.log(f"  温度平均值: {df_results['temp_mean'].mean():.2f} °C")
        self.log(f"  温度范围: {df_results['temp_mean'].min():.2f} - {df_results['temp_mean'].max():.2f}")
        self.log(f"  年均降水量: {df_results['precip_annual'].mean():.1f} mm/year")
        
        # 按省份统计
        self.log("\n【省份统计 (Top 10)】")
        province_stats = df_results.groupby('province').agg({
            'ghi_mean': 'mean',
            'temp_mean': 'mean',
            'precip_annual': 'mean'
        }).sort_values('ghi_mean', ascending=False).head(10)
        
        for prov, row in province_stats.iterrows():
            self.log(f"  {prov}: GHI={row['ghi_mean']:.2f}, "
                    f"Temp={row['temp_mean']:.1f}°C, "
                    f"Precip={row['precip_annual']:.0f}mm/year")
        
        self.log("\n" + "="*70)
        self.log("所有数据已保存完成！")
        self.log("="*70)
    
    def retry_failed(self, delay=1.0):
        """重试失败的记录"""
        if not self.failed_indices:
            self.log("没有失败的记录需要重试")
            return
        
        self.log(f"\n开始重试 {len(self.failed_indices)} 个失败的记录...")
        
        retry_failed = []
        for idx in self.failed_indices:
            row = self.gdf.iloc[idx]
            lat, lon = row['lat'], row['lon']
            
            try:
                data = self.api.get_solar_data(lat, lon)
                
                if data:
                    result = {
                        'index': idx,
                        'province': row['province'],
                        'lon': lon,
                        'lat': lat,
                        'area_km2': row['area_km2'],
                        'ghi_mean': data['ghi_annual_mean'],
                        'ghi_std': data['ghi_annual_std'],
                        'temp_mean': data['temp_annual_mean'],
                        'temp_std': data['temp_annual_std'],
                        'precip_annual': data['precip_annual_mean'],  # 年均降水量
                    }
                    self.results.append(result)
                    self.log(f"  ✓ 索引 {idx} 重试成功")
                else:
                    retry_failed.append(idx)
                    
            except Exception as e:
                retry_failed.append(idx)
                self.log(f"  ✗ 索引 {idx} 重试失败: {e}")
            
            time.sleep(delay)
        
        self.failed_indices = retry_failed
        self.log(f"\n重试完成: 成功 {len(self.failed_indices)} 个")


def main():
    """主函数"""
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║   CPVPD-2024 太阳辐射数据批量获取工具                           ║
    ║   Solar Radiation Data Fetcher for PV Stations                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # 配置
    data_dir = "CPVPD-2024_4326"
    output_dir = "solar_data_output"
    
    # 创建获取器
    fetcher = SolarDataFetcher(data_dir, output_dir)
    
    # 加载数据
    fetcher.load_data()
    
    # 检查是否有进度
    has_progress = fetcher.load_progress()
    
    # 询问用户
    if has_progress:
        response = input("\n发现之前的进度，是否继续？(y/n): ").strip().lower()
        if response != 'y':
            print("已取消")
            return
    
    # 开始获取
    try:
        fetcher.fetch_all(delay=0.6, save_interval=50)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        fetcher.save_progress(fetcher.start_index)
        print("进度已保存，下次可以继续")
        return
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        fetcher.save_progress(fetcher.start_index)
        print("进度已保存")
        raise
    
    # 重试失败的
    if fetcher.failed_indices:
        response = input(f"\n有 {len(fetcher.failed_indices)} 个记录失败，是否重试？(y/n): ").strip().lower()
        if response == 'y':
            fetcher.retry_failed(delay=1.0)
    
    # 保存结果
    fetcher.save_results()
    
    print("\n✅ 全部完成！")
    print(f"数据文件: {fetcher.output_csv}")
    print(f"日志文件: {fetcher.log_file}")


if __name__ == "__main__":
    main()
