import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Radler & Gose - Officiel", layout="wide")

# --- MAPPING OFFICIEL MIS À JOUR AVEC VOS CODES ---
SKU_MAPPING = {
    "JLGL": "GOSE LIME 3.9%",
    "JLML": "MEXICAINE LIME 4.5%",
    "JLRC": "RADLER CLEMENTINE 3.5%",
    "JLBBC": "BLANCHE BELGE CLEMENTINE 5%"
}

# L'ordre exact pour vos onglets Excel
SKU_ORDER = [
    "GOSE LIME 3.9%", 
    "MEXICAINE LIME 4.5%", 
    "RADLER CLEMENTINE 3.5%",
    "BLANCHE BELGE CLEMENTINE 5%"
]

st.title("🍹 Extracteur de Ventes : Gamme Radler, Gose & Blanche")
st.info("Cette application utilise les codes : JLGL, JLML, JLRC et JLBBC.")

uploaded_file = st.file_uploader("Glissez le fichier CSV ici", type="csv")

if uploaded_file:
    try:
        # 1. Lecture brute pour détecter le séparateur (, ou ;)
        raw_bytes = uploaded_file.getvalue()
        raw_text = raw_bytes.decode('latin1').split('\n')[0]
        sep = ';' if ';' in raw_text else ','
        uploaded_file.seek(0)
        
        df = pd.read_csv(uploaded_file, encoding='latin1', sep=sep)
        
        # 2. Nettoyage des noms de colonnes (espaces invisibles)
        df.columns = df.columns.str.strip()

        # 3. Nettoyage des données numériques
        for col in ['LineQty', 'LineTotal', 'Rabais']:
            if col in df.columns:
                # Gestion des virgules québécoises et des espaces
                df[col] = df[col].astype(str).str.replace(r'[^\d,.-]', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 4. Nettoyage des codes items et Mapping
        df['ItemCode_Clean'] = df['ItemCode'].astype(str).str.strip()
        df['Nom_Propre'] = df['ItemCode_Clean'].map(SKU_MAPPING)

        # --- SECTION DIAGNOSTIC ---
        st.subheader("📊 État du traitement")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Transactions lues", len(df))
        with c2:
            st.metric("Total Caisses (Brut)", f"{df['LineQty'].sum():.1f}")
        with c3:
            reconnus = df['Nom_Propre'].notna().sum()
            st.metric("Lignes reconnues (Mapping)", reconnus)

        if reconnus == 0 and len(df) > 0:
            st.error("⚠️ Aucun produit reconnu. Vérifiez que la colonne 'ItemCode' contient bien JLGL, JLML, JLRC ou JLBBC.")
            st.write("Codes détectés dans votre fichier :", df['ItemCode_Clean'].unique().tolist())

        # 5. Création des rapports avec ordre fixe
        def force_order(data_df):
            base = pd.DataFrame({'Nom_Propre': SKU_ORDER})
            merged = pd.merge(base, data_df, on='Nom_Propre', how='left').fillna(0)
            return merged.rename(columns={'Nom_Propre': 'ItemName'})

        # Calculs des onglets
        res_sku = force_order(df.groupby('Nom_Propre')['LineQty'].sum().reset_index())
        
        # Ventes par jour
        if 'DocDate' in df.columns:
            res_jour = df.pivot_table(index='Nom_Propre', columns='DocDate', values='LineQty', aggfunc='sum', fill_value=0).reset_index()
            res_jour = force_order(res_jour)
        else:
            res_jour = pd.DataFrame(columns=["Erreur: Colonne DocDate manquante"])

        # Financier
        res_fin = df.groupby('Nom_Propre').agg({'LineTotal': 'sum', 'Rabais':
