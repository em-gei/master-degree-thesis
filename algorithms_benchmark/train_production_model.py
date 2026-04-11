import pandas as pd
import glob
import joblib
from lightgbm import LGBMClassifier

# 1. Load data
all_files = glob.glob("*.csv")
if not all_files:
    raise FileNotFoundError("ERROR: No CSV files found.")

df_list = []
rolling_window = 6

for f in all_files:
    temp_df = pd.read_csv(f).sort_values('Timestamp')
    
    temp_df['EAR_mean_3s'] = temp_df['Cam_EAR'].rolling(window=rolling_window, min_periods=1).mean()
    temp_df['EAR_min_3s'] = temp_df['Cam_EAR'].rolling(window=rolling_window, min_periods=1).min()
    temp_df['Pitch_std_3s'] = temp_df['Cam_Pitch'].rolling(window=rolling_window, min_periods=1).std().fillna(0)
    temp_df['Yaw_std_3s'] = temp_df['Cam_Yaw'].rolling(window=rolling_window, min_periods=1).std().fillna(0)
    temp_df['Gyro_X_std_3s'] = temp_df['Gyro_Acc_X'].rolling(window=rolling_window, min_periods=1).std().fillna(0)
    temp_df['Gyro_Y_std_3s'] = temp_df['Gyro_Acc_Y'].rolling(window=rolling_window, min_periods=1).std().fillna(0)
    temp_df['Gyro_Z_std_3s'] = temp_df['Gyro_Acc_Z'].rolling(window=rolling_window, min_periods=1).std().fillna(0)
    
    df_list.append(temp_df)

df = pd.concat(df_list, ignore_index=True)

# 2. Clean data
# Remove unwanted labels (CRASH/EBBREZZA) and merge 'NERVOSO' into 'VIGILE'
if 'Label_ML' in df.columns:
    df = df[~df['Label_ML'].isin(['EBBREZZA', 'CRASH'])].reset_index(drop=True)
    df['Label_ML'] = df['Label_ML'].replace({'NERVOSO': 'VIGILE'})

# 3. Select exclusive feature for ML algorithm (BehavioralUnit)
production_features = [
    'EAR_mean_3s', 'EAR_min_3s', 'Pitch_std_3s', 'Yaw_std_3s', 
    'Gyro_X_std_3s', 'Gyro_Y_std_3s', 'Gyro_Z_std_3s'
]

# Drop rows with NaN
df = df.dropna(subset=production_features)

X = df[production_features]
y = df['Label_ML']

# 4. Training the Final Model
model = LGBMClassifier(n_estimators=100, class_weight='balanced', random_state=42, n_jobs=-1, verbose=-1)
model.fit(X, y)

# 5. Save the artifact
model_filename = 'lightgbm_model.pkl'
joblib.dump(model, model_filename)

print(f"Training completed! Model saved as '{model_filename}'.")
print(f"Expected features from the model: {list(X.columns)}")