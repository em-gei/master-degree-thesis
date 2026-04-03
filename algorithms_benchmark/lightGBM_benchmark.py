import pandas as pd
import numpy as np
import glob
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, ConfusionMatrixDisplay, matthews_corrcoef
from lightgbm import LGBMClassifier

print("Phase 1: Data Loading and Temporal Engineering (3-second Rolling Windows)...")
all_files = glob.glob("*.csv")
df_list = []
rolling_window = 6  # 6 rows == 3 seconds (at 2 Hz)

if not all_files:
    print("ERROR: No CSV files found.")
else:
    # --- PHASE 1: DATA MERGE AND ROLLING WINDOWS CREATION ---
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

    # Combine all dataframes
    df = pd.concat(df_list, ignore_index=True)

    # --- PHASE 2: DATA CLEANING ---
    print(f"Merged dataset created: {df.shape[0]} rows and {df.shape[1]} columns.")

    # Remove unwanted labels (CRASH/EBBREZZA) and merge 'NERVOSO' into 'VIGILE'
    if 'Label_ML' in df.columns:
        df = df[~df['Label_ML'].isin(['EBBREZZA', 'CRASH'])].reset_index(drop=True)
        df['Label_ML'] = df['Label_ML'].replace({'NERVOSO': 'VIGILE'})

    # Drop environmental columns to prevent data leakage
    #columns_to_drop = ['Timestamp', 'Label_ML']
    columns_to_drop = ['Timestamp', 'Label_ML', 'Temp_C', 'Humidity_Perc', 'Light_Lux']
    discarded_columns = [c for c in columns_to_drop if c in df.columns]

    X = df.drop(columns=discarded_columns)
    y = df['Label_ML']

    # Split into training and testing sets (Stratified)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # --- PHASE 3: MODEL TRAINING ---
    print("\nTraining LightGBM with Time Windows in progress...")
    model = LGBMClassifier(n_estimators=100, class_weight='balanced', random_state=42, n_jobs=-1, verbose=-1)
    model.fit(X_train, y_train)

    # --- PHASE 4: EVALUATION ---
    y_pred = model.predict(X_test)
    mcc = matthews_corrcoef(y_test, y_pred)
    print("\n\033[1m LIGHT GBM CLASSIFICATION REPORT \033[0m")
    print(f"\n Matthews Correlation Coefficient (MCC): \033[1m{mcc:.4f}\033[0m \n")
    print(classification_report(y_test, y_pred, zero_division=0))

    # --- PHASE 5: FEATURE IMPORTANCE ---
    importances = model.feature_importances_
    feature_imp_df = pd.DataFrame({
        'Sensor': X.columns,
        'Importance_Score': importances
    }).sort_values('Importance_Score', ascending=False)

    # --- PHASE 6: PLOTTING ---
    fig, ax = plt.subplots(1, 2, figsize=(18, 7))

    # Graph 1: Feature Importances
    feature_imp_df.head(10).plot(kind='bar', x='Sensor', y='Importance_Score', ax=ax[0], color='teal', legend=False)
    ax[0].set_title('LightGBM Top 10 Metrics', fontsize=14, fontweight='bold')
    ax[0].set_ylabel('Impact on Decision (Split Count)', fontsize=14)
    ax[0].set_xlabel('Metrics', fontsize=14)
    ax[0].tick_params(axis='both', labelsize=14)
    ax[0].set_xticklabels(ax[0].get_xticklabels(), rotation=45, ha='right')

    # Graph 2: Confusion Matrix
    ConfusionMatrixDisplay.from_estimator(
        model, X_test, y_test,
        ax=ax[1],
        cmap='Blues',
        xticks_rotation=45,
        text_kw={'fontsize': 16, 'fontweight': 'bold'}
    )
    ax[1].set_title('LightGBM Confusion Matrix', fontsize=14, fontweight='bold')
    ax[1].set_xlabel('Predicted label', fontsize=14)
    ax[1].set_ylabel('True label', fontsize=14)
    ax[1].tick_params(axis='both', labelsize=14)

    plt.tight_layout()
    plt.show()
    print("\nScript execution completed.")