import pickle
import numpy as np

model_path = 'models/models/model_gat_gbdt_pvssi.pkl'

with open(model_path, 'rb') as f:
    model = pickle.load(f)

print('=== 检查特征列 ===')
print('feature_cols:', model['feature_cols'])

print()
print('=== 检查训练数据范围 ===')
train_features = model['train_features']
print(f'训练特征形状: {train_features.shape}')
print(f'训练特征列数: {train_features.shape[1]}')

print()
print('=== 检查 PVSSI_rule 范围 ===')
pvssi_values = model['train_df_minimal']['PVSSI_rule']
print(f'PVSSI_rule 最小值: {pvssi_values.min()}')
print(f'PVSSI_rule 最大值: {pvssi_values.max()}')
print(f'PVSSI_rule 平均值: {pvssi_values.mean()}')

print()
print('=== 检查两个GBDT模型的预测差异 ===')
gbdt_models = model['gbdt_models']

# 测试第一个训练样本
X_test = model['train_features'][:1]
print('第一个训练样本:', X_test[0])

print()
preds = []
for i, item in enumerate(gbdt_models):
    if isinstance(item, tuple) and len(item) >= 2:
        model_obj = item[1]
        name = item[0]
    else:
        model_obj = item
        name = f'模型{i}'
    
    pred = model_obj.predict(X_test)
    preds.append(pred[0])
    print(f'{name} 预测: {pred[0]}')

print()
print(f'预测值差异: {abs(preds[0] - preds[1])}')

print()
print('=== 测试标准化特征的预测 ===')
X_scaled = model['x_scaler'].transform(X_test)
print('标准化后样本:', X_scaled[0])

print()
for i, item in enumerate(gbdt_models):
    if isinstance(item, tuple) and len(item) >= 2:
        model_obj = item[1]
        name = item[0]
    else:
        model_obj = item
        name = f'模型{i}'
    
    pred = model_obj.predict(X_scaled)
    print(f'{name} 使用标准化特征预测: {pred[0]}')
