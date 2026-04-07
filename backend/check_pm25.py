import pandas as pd

df = pd.read_csv('sensor_cleaned.csv')
print('PM2.5 null 수:', df['pm25'].isna().sum())
print('PM2.5 전체 수:', len(df))
print('PM2.5 unique 값 수:', df['pm25'].nunique())
print(df['pm25'].describe())