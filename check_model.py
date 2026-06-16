import pickle
import numpy as np

model_path = 'models/models/model_gat_gbdt_pvssi.pkl'

with open(model_path, 'rb') as f:
    model = pickle.load(f)

print('=== 检查 gbdt_models 结构 ===')
gbdt_models = model['gbdt_models']
if isinstance(gbdt_models, dict):
    print('是字典类型')
    print('键:', list(gbdt_models.keys()))
    gbdt_models = list(gbdt_models.values())
else:
    print(f'是 {type(gbdt_models)} 类型')

print(f'模型数量: {len(gbdt_models)}')

for i, item in enumerate(gbdt_models):
    if isinstance(item, tuple):
        print(f'模型{i}: 元组格式，长度={len(item)}')
        print(f'  名称: {item[0]}')
        print(f'  类型: {type(item[1])}')
    else:
        print(f'模型{i}: 直接是模型对象')
        print(f'  类型: {type(item)}')

print()
print('=== 测试预测（使用第一个训练样本）===')
X_test = model['train_features'][:1]
print('输入特征:', X_test)
print()

preds = []
for i, item in enumerate(gbdt_models):
    if isinstance(item, tuple) and len(item) >= 2:
        model_obj = item[1]
    else:
        model_obj = item
    
    pred = model_obj.predict(X_test)
    preds.append(pred[0])
    print(f'GBDT {i} 预测: {pred[0]}')

print()
print(f'预测值列表: {preds}')
print(f'平均值: {np.mean(preds)}')

print()
print('=== 测试预测（使用一个新样本）===')
# 构造一个新样本（上海附近）
new_sample = np.array([[121.47, 31.23, 
                       np.cos(np.radians(31.23)) * np.cos(np.radians(121.47)),
                       np.cos(np.radians(31.23)) * np.sin(np.radians(121.47)),
                       np.sin(np.radians(31.23)),
                       np.log1p(0.0456),  # log_area 使用中位数
                       3.85,  # ghi_mean
                       1.86,  # ghi_std
                       17.7,  # temp_mean
                       8.75,  # temp_std
                       1496,  # precip_annual
                       71,    # cluster_count
                       5.0]]) # nearest_station_km

print('新样本:', new_sample)
print()

preds_new = []
for i, item in enumerate(gbdt_models):
    if isinstance(item, tuple) and len(item) >= 2:
        model_obj = item[1]
    else:
        model_obj = item
    
    pred = model_obj.predict(new_sample)
    preds_new.append(pred[0])
    print(f'GBDT {i} 预测: {pred[0]}')

print()
print(f'新样本预测值列表: {preds_new}')
print(f'新样本平均值: {np.mean(preds_new)}')
