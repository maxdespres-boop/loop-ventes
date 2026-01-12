import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Radler & Gose - Officiel", layout="wide")

# --- MAPPING OFFICIEL ---
SKU_MAPPING = {
    "JLGL": "GOSE LIME 3.9%",
    "JLML": "MEXICAINE LIME 4.5%",
    "JLRC": "RADLER CLEMENTINE 3.5%",
    "JLBBC": "BLANCHE BELGE CLEMENTINE 5%"
}

SKU_ORDER = [
    "GOSE LIME 3.9%", 
    "MEXICAINE LIME 4.5%", 
    "RADLER CLEMENTINE 3.5%",
    "BLANCHE BELGE CLEMENTINE 5%"
]

st.title("🍹 Extracteur de Ventes : Gamme Radler, Gose & Blanche")

uploaded_file = st.file_uploader("Glissez le fichier CSV ici", type="csv")

if uploaded_file:
    try:
        # 1. Lecture brute et détection du séparateur
        raw_bytes = uploaded_file.getvalue()
        raw_text = raw_bytes.decode('latin1').split('\n')[0]
        sep = ';' if ';' in raw_text else ','
        uploaded_file.seek(0)
        
        df = pd.read_csv(uploaded_file, encoding='latin1', sep=sep)
        
        # 2. Nettoyage des noms de colonnes
        df.columns = df.columns.str.strip()

        # 3. Nettoyage des données numériques
        for col in ['LineQty', 'LineTotal', 'Rabais']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'[^\d,.-]', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 4. Nettoyage des codes items et Mapping (LIGNE CORRIGÉE ICI)
        df['ItemCode_Clean'] = df['ItemCode'].astype(str).str.strip()
        df['Nom_Propre'] = df['ItemCode_Clean'].map(SKU_MAPPING)

        #
