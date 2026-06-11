import pandas as pd
df = pd.read_csv('dashboard/public/data/provincial_statistics.csv')
total_area = df["Total_Area_km2"].sum()
total_count = df["Count"].sum()
print(f'Total Area: {total_area:.2f} km2')
print(f'Total Stations: {total_count}')
