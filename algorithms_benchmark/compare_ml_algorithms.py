# PRE-REQUISITE ON COLAB: !pip install catboost confidence-ensembles pyod
import pandas as pd
import numpy as np
import glob
import time
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, matthews_corrcoef
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
from confens.classifiers.ConfidenceBagging import ConfidenceBagging
from confens.classifiers.ConfidenceBoosting import ConfidenceBoosting

print("STARTING ALGORITHM BENCHMARK")

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

# Encode labels to numeric formats (required by XGBoost, CatBoost, etc.)
label_encoder = LabelEncoder()
y = label_encoder.fit_transform(y_raw)

# Split Train/Test with Stratification
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Convert to NumPy arrays: confens uses numpy-style indexing (X[:, features])
# which fails on DataFrames. All sklearn-compatible models accept arrays.
X_train_np = X_train.to_numpy()
X_test_np = X_test.to_numpy()

# --- 2. DEFINE THE MODELS ---
# Configure a base decision tree to feed into the confidence ensembles
base_tree = DecisionTreeClassifier(class_weight='balanced', random_state=42)
rf_classifier=RandomForestClassifier(n_estimators=50)
models = {
    "LightGBM": LGBMClassifier(class_weight='balanced', random_state=42, n_jobs=-1, verbose=-1),
    "XGBoost": XGBClassifier(random_state=42, n_jobs=-1, eval_metric='mlogloss'),
    "CatBoost": CatBoostClassifier(random_state=42, verbose=0, auto_class_weights='Balanced'),
    "Decision Tree": base_tree,
    "Extra Trees": ExtraTreesClassifier(class_weight='balanced', random_state=42, n_jobs=-1),
    "Random Forest": RandomForestClassifier(class_weight='balanced', random_state=42, n_jobs=-1),
    "Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=2000, random_state=42)),
    "Multi-Layer Perceptron": make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=1000, random_state=42)),
    "Support Vector Machine": make_pipeline(StandardScaler(), SVC(kernel='rbf', class_weight='balanced', random_state=42)),
    "ConfBag": ConfidenceBagging(clf=rf_classifier, n_base=10, max_features=0.7, sampling_ratio=0.7),
    "ConfBoost": ConfidenceBoosting(clf=rf_classifier, n_base=10, learning_rate=2, sampling_ratio=0.5, conf_thr=0.8)
}

results = []
print("\nTraining in progress...\n")

# --- 3. BENCHMARKING LOOP ---
for name, model in models.items():

    print(f"Evaluating: {name}...")

    # confens models require NumPy arrays (they use X[:, features] slicing)
    is_confens = isinstance(model, (ConfidenceBagging, ConfidenceBoosting))
    X_tr = X_train_np if is_confens else X_train
    X_te = X_test_np if is_confens else X_test

    # Train
    model.fit(X_tr, y_train)
    # Predict
    y_pred = model.predict(X_te)

    # Global metrics (Macro Averaged per equità sulle classi sbilanciate)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='macro', zero_division=0)
    rec = recall_score(y_test, y_pred, average='macro', zero_division=0)
    f1 = f1_score(y_test, y_pred, average='macro', zero_division=0)

    # Matthews Correlation Coefficient
    mcc = matthews_corrcoef(y_test, y_pred)

    # Confusion Matrix to extract total TP, TN, FP, FN
    cm = confusion_matrix(y_test, y_pred)
    FP = cm.sum(axis=0) - np.diag(cm)
    FN = cm.sum(axis=1) - np.diag(cm)
    TP = np.diag(cm)
    TN = cm.sum() - (FP + FN + TP)
    total_TP = int(sum(TP))
    total_FP = int(sum(FP))
    total_FN = int(sum(FN))
    total_TN = int(sum(TN))

    # Inference Latency (Real-Time Edge Simulation)
    single_sample = X_te[[0]] if is_confens else X_test.iloc[[0]]
    start_inf = time.time()
    for _ in range(1000):
        model.predict(single_sample)
    inf_time_ms = ((time.time() - start_inf) / 1000) * 1000

    results.append({
        "Model": name,
        "Total_TP": total_TP,
        "Total_TN": total_TN,
        "Total_FP": total_FP,
        "Total_FN": total_FN,
        "Accuracy": f"{acc:.4f}",
        "Precision (Macro)": f"{prec:.4f}",
        "Recall (Macro)": f"{rec:.4f}",
        "F1-Score (Macro)": f"{f1:.4f}",
        "MCC (Correlation)": f"{mcc:.4f}",
        "Latency (ms)": round(inf_time_ms, 3)
    })

# --- 4. PRINT FINAL RESULTS ---
df_risultati = pd.DataFrame(results)

# Sort by decreasing MCC (the best metric) and then by increasing latency
df_risultati = df_risultati.sort_values(by=["MCC (Correlation)", "Latency (ms)"], ascending=[False, True]).reset_index(drop=True)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print("\n MODELS RANKING")
print("-" * 120)
print(df_risultati.to_string(index=False))
print("-" * 120)
