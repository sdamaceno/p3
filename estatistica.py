import pandas as pd

def processar_precos_regra(df, regra):
    if df.empty: return df, pd.DataFrame(), 0, 0, 0
    mediana_geral = df['Preço'].median()
    limite_inferior = mediana_geral * 0.75
    limite_superior = mediana_geral * 1.25
    df_validos = df[(df['Preço'] >= limite_inferior) & (df['Preço'] <= limite_superior)].copy()
    df_outliers = df[(df['Preço'] < limite_inferior) | (df['Preço'] > limite_superior)].copy()
    return df_validos, df_outliers, mediana_geral, limite_inferior, limite_superior

def ordenar_validos(df):
    if df.empty: return df
    return df.sort_values(by=['Preço'])

def ordenar_outliers(df):
    if df.empty: return df
    idx_max = df['Preço'].idxmax()
    idx_min = df['Preço'].idxmin()
    row_max = df.loc[[idx_max]]
    if idx_max == idx_min: return row_max
    row_min = df.loc[[idx_min]]
    restante = df.drop([idx_max, idx_min], errors='ignore')
    return pd.concat([row_max, row_min, restante])