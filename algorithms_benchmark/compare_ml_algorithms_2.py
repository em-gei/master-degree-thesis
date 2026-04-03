# PRE-REQUISITE ON COLAB: !pip install catboost
import pandas as pd
import numpy as np
import glob
import time
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import make_pipeline
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

print("STARTING THE SAFETY-CRITICAL BENCHMARK (ASYMMETRIC ERROR FOCUS)...")

# --- 1. LOAD AND PREPARE DATASET ---
all_files = glob.glob("*.csv")
if not all_files:
    raise FileNotFoundError("CSV files not found!")

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

# Architecture: 4 Classes, No Weather Data
df = df[~df['Label_ML'].isin(['CRASH', 'EBBREZZA'])]
df['Label_ML'] = df['Label_ML'].replace('NERVOSO', 'VIGILE')
discarded_columns = [c for c in ['Timestamp', 'Label_ML', 'Temp_C', 'Humidity_Perc', 'Light_Lux'] if c in df.columns]

X = df.drop(columns=discarded_columns)
y_raw = df['Label_ML']

# Encode labels for XGBoost compatibility
label_encoder = LabelEncoder()
y = label_encoder.fit_transform(y_raw)

# Split Train/Test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# --- 2. DEFINE THE MODELS ---
models = {
    "LightGBM": LGBMClassifier(class_weight='balanced', random_state=42, n_jobs=-1, verbose=-1),
    "XGBoost": XGBClassifier(random_state=42, n_jobs=-1, eval_metric='mlogloss'),
    "CatBoost": CatBoostClassifier(random_state=42, verbose=0, auto_class_weights='Balanced'),
    "Decision Tree": DecisionTreeClassifier(class_weight='balanced', random_state=42),
    "Extra Trees": ExtraTreesClassifier(class_weight='balanced', random_state=42, n_jobs=-1),
    "Random Forest": RandomForestClassifier(class_weight='balanced', random_state=42, n_jobs=-1),
    "Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=2000, random_state=42)),
    "Multi-Layer Perceptron": make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=1000, random_state=42)),
    "Support Vector Machine": make_pipeline(StandardScaler(), SVC(kernel='rbf', class_weight='balanced', random_state=42))
}

results = []
print("\nTraining in progress...\n")

# --- 3. BENCHMARKING LOOP ---
for name, model in models.items():
    print(f"Evaluating: {name}...")

    # Train
    model.fit(X_train, y_train)
    # Predict
    y_pred = model.predict(X_test)
    # Decode numeric labels back to strings to extract specific classes
    y_test_str = label_encoder.inverse_transform(y_test)
    y_pred_str = label_encoder.inverse_transform(y_pred)

    # Global Accuracy
    acc = accuracy_score(y_test_str, y_pred_str)

    # Extract specific Recalls
    report_dict = classification_report(y_test_str, y_pred_str, output_dict=True, zero_division=0)
    recall_sonnolenza = report_dict.get('SONNOLENZA', {}).get('recall', 0.0)
    recall_malore = report_dict.get('MALORE', {}).get('recall', 0.0)

    # Measure Inference Latency (Real-Time Simulation)
    single_sample = X_test.iloc[[0]]
    start_inf = time.time()
    for _ in range(1000):
        model.predict(single_sample)
    inf_time_ms = ((time.time() - start_inf) / 1000) * 1000

    results.append({
        "Model": name,
        "Global Accuracy": f"{acc:.2%}",
        "Recall SONNOLENZA": f"{recall_sonnolenza:.2%}",
        "Recall MALORE": f"{recall_malore:.2%}",
        "Latency (ms)": round(inf_time_ms, 3)
    })

# --- 4. PRINT FINAL RESULTS ---
df_risultati = pd.DataFrame(results)

# Sort primarily by the Critical Recalls (Sonnolenza + Malore), then by lowest Latency
df_risultati['Critical_Score'] = df_risultati['Recall SONNOLENZA'].str.rstrip('%').astype('float') + df_risultati['Recall MALORE'].str.rstrip('%').astype('float')
df_risultati = df_risultati.sort_values(by=["Critical_Score", "Latency (ms)"], ascending=[False, True]).drop(columns=['Critical_Score']).reset_index(drop=True)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print("\n CRITICAL SAFETY RANKING (Sorted by ability to detect Sonnolenza & Malore)")
print("-" * 90)
print(df_risultati.to_string(index=False))
print("-" * 90)
