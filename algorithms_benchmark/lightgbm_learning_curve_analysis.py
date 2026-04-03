import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO
import numpy as np

# 1. CSV data for LightGBM tests
csv_data = """Test_Num,Numero_Righe,Meteo,Nervoso_in_Vigile,Acc_Globale,Recall_Distrazione,Recall_Sonnolenza,Recall_Malore,Recall_Nervoso,MCC
1,1157,Y,N,0.98,0.84,NaN,1.00,NaN,0.9063
2,4521,Y,N,0.97,0.90,0.97,0.78,0.86,0.9138
3,8100,Y,N,0.94,0.88,0.93,0.85,0.90,0.8823
4,10175,Y,N,0.94,0.87,0.93,0.89,0.90,0.8833
5,14506,Y,N,0.93,0.91,0.92,0.86,0.89,0.8639
6,16085,Y,N,0.93,0.90,0.96,0.83,0.91,0.8626
7,18359,Y,N,0.93,0.90,0.94,0.88,0.93,0.8615
8,1157,N,N,0.99,0.92,NaN,1.00,NaN,0.9446
9,4521,N,N,0.93,0.85,0.83,0.78,0.66,0.7992
10,8100,N,N,0.88,0.78,0.84,0.79,0.71,0.7467
11,10175,N,N,0.89,0.87,0.85,0.89,0.71,0.7848
12,14506,N,N,0.87,0.85,0.84,0.78,0.78,0.7473
13,16085,N,N,0.87,0.83,0.83,0.81,0.77,0.7294
14,18359,N,N,0.87,0.81,0.91,0.80,0.80,0.7313
15,1157,N,Y,0.99,0.92,NaN,1.00,NaN,0.9446
16,4521,N,Y,0.96,0.88,0.77,0.78,NaN,0.8658
17,8100,N,Y,0.93,0.80,0.92,0.75,NaN,0.8081
18,10175,N,Y,0.93,0.80,0.86,0.90,NaN,0.8096
19,14506,N,Y,0.92,0.83,0.88,0.79,NaN,0.7890
20,16085,N,Y,0.91,0.82,0.87,0.82,NaN,0.7691
21,18359,N,Y,0.91,0.83,0.89,0.80,NaN,0.7730"""

# 2. Load the CSV data into a DataFrame
df = pd.read_csv(StringIO(csv_data))

# Get scenarios based on 'Meteo' and 'Nervoso_in_Vigile' columns
def get_scenario(row):
    meteo = "Con Meteo (Bias)" if row['Meteo'] == 'Y' else "Senza Meteo"
    classi = "4 Classi (No Nervoso)" if row['Nervoso_in_Vigile'] == 'Y' else "5 Classi (Con Nervoso)"
    return f"{meteo} | {classi}"

df['Scenario'] = df.apply(get_scenario, axis=1)

# Clean and sort the DataFrame
df = df.dropna(subset=['Numero_Righe'])
df = df.sort_values(by=['Numero_Righe', 'Scenario'])

# 3. Graph settings
sns.set_theme(style="whitegrid", context="talk")
fig, axes = plt.subplots(2, 2, figsize=(22, 16))
color_dict = {
    "Senza Meteo | 4 Classi (No Nervoso)": "#2ca02c",  # best scenario
    "Senza Meteo | 5 Classi (Con Nervoso)": "#1f77b4",
    "Con Meteo (Bias) | 5 Classi (Con Nervoso)": "#d62728"  # worst scenario (with bias)
}
style_dict = {
    "Senza Meteo | 4 Classi (No Nervoso)": "",                  # Continuous line
    "Senza Meteo | 5 Classi (Con Nervoso)": (4, 1.5),           # Dashed line
    "Con Meteo (Bias) | 5 Classi (Con Nervoso)": (1, 1)         # Dotted line
}

# Helper function for plotting graphs
def plot_metric(ax, metric, title):
    sns.lineplot(data=df, x='Numero_Righe', y=metric,
                 hue='Scenario', style='Scenario',
                 palette=color_dict, dashes=style_dict,
                 markers=True, markersize=10, linewidth=3, ax=ax)

    ax.set_title(title, fontsize=18, fontweight='bold', pad=15)
    ax.set_ylim(0.30, 1.05)
    ax.set_ylabel("Punteggio Recall (0.0 - 1.0)", fontsize=14)
    ax.set_xlabel("Numero di Record nel Dataset", fontsize=14)
    ax.tick_params(axis='both', labelsize=12)
    # Legend shown only in the first graph
    if ax != axes[0,0]:
        if ax.get_legend() is not None:
            ax.get_legend().remove()

# 4. Generation of the 4 Quadrants
plot_metric(axes[0,0], 'Recall_Sonnolenza', 'Apprendimento: SONNOLENZA (Critico)')
plot_metric(axes[0,1], 'Recall_Malore', 'Apprendimento: MALORE (Critico)')
plot_metric(axes[1,0], 'Recall_Distrazione', 'Apprendimento: DISTRAZIONE')
plot_metric(axes[1,1], 'Recall_Nervoso', 'Apprendimento: NERVOSO (Limite Fisico)')

# Put the legend only in the first graph
axes[0,0].legend(title="Legenda Scenari (LightGBM)", title_fontsize=14, fontsize=12,
                 loc='lower right', frameon=True, shadow=True)

plt.suptitle("Analisi della Curva di Apprendimento (LightGBM)\nValutazione su Dimensione del Dataset e Configurazione Sensori",
             fontsize=24, fontweight='bold', y=1.03)

plt.tight_layout()
plt.savefig('lightgbm_learning_curve_scenari.png', dpi=300, bbox_inches='tight')
plt.show()