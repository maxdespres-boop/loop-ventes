import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Radler & Gose - Fix", layout="wide")

# On définit le mapping (Assurez-vous que les codes MAGOSL12 etc. sont EXACTS dans votre CSV)
SKU_MAPPING = {
    "MAGOSL12": "GOSE LIME 3.9%",
    "MAMEXL12": "MEXICAINE LIME 4.5%",
    "MARADC12": "RADLER CLEMENTINE 3.5%"
}
SKU_ORDER = ["GOSE LIME 3.9%", "MEXICAINE LIME 4.5%", "RADLER CLEMENTINE 3.5%"]

st.title("🍹 Extracteur : Gamme Radler & Gose (Version Corrigée)")

uploaded_file = st.file_uploader("Glissez le fichier CSV ici", type="csv")

if uploaded_file:
    try:
        # 1. Lecture flexible (détection du séparateur , ou ;)
        df = pd.read_csv(uploaded_file, encoding='latin1', sep=None, engine='python')
        
        # 2. NETTOYAGE DES COLONNES : on enlève les espaces invisibles autour des titres
        df.columns = df.columns.str.strip()
        
        # 3. NETTOYAGE DES DONNÉES : on enlève les espaces dans ItemCode et ItemName
        if 'ItemCode' in df.columns:
            df['ItemCode'] = df['ItemCode'].astype(str).str.strip()
        if 'ItemName' in df.columns:
            df['ItemName'] = df['ItemName'].astype(str).str.strip()

        # 4. NETTOYAGE NUMÉRIQUE : gestion virgule/point et espaces
        for col in ['LineQty', 'LineTotal', 'Rabais']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'[^\d,.-]', '', regex=True) # Enlever symboles monétaires ou espaces
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 5. Application du mapping
        df['Nom_Propre'] = df['ItemCode'].map(SKU_MAPPING).fillna(df['ItemName'])

        # Vérification pour le debug (visible seulement sur l'app)
        if df['LineQty'].sum() == 0:
            st.warning("⚠️ Attention : Le total des quantités est toujours à 0. Vérifiez les noms des colonnes dans votre CSV.")
            st.write("Colonnes détectées :", list(df.columns))

        def force_order(data_df):
            base = pd.DataFrame({'Nom_Propre': SKU_ORDER})
            merged = pd.merge(base, data_df, on='Nom_Propre', how='left').fillna(0)
            return merged.rename(columns={'Nom_Propre': 'ItemName'})

        # Calculs
        res_sku = force_order(df.groupby('Nom_Propre')['LineQty'].sum().reset_index())
        res_jour = force_order(df.pivot_table(index='Nom_Propre', columns='DocDate', values='LineQty', aggfunc='sum', fill_value=0).reset_index())
        res_fin = force_order(df.groupby('Nom_Propre').agg({'LineTotal': 'sum', 'Rabais': 'sum'}).reset_index())

        # Export Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_sku.to_excel(writer, sheet_name='SKU_Caisses', index=False)
            res_jour.to_excel(writer, sheet_name='SKU_Par_Jour', index=False)
            res_fin.to_excel(writer, sheet_name='SKU_Financier', index=False)
            
            # Ajustement automatique des colonnes
            for sheet in writer.sheets:
                writer.sheets[sheet].set_column(0, 0, 30)

        st.success("✅ Analyse terminée.")
        st.download_button("📥 Télécharger Excel", output.getvalue(), "Ventes_Radler_Gose.xlsx")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
