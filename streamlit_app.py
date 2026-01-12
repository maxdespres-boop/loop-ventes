import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Radler & Gose - Diagnostic", layout="wide")

# --- MAPPING OFFICIEL ---
# Assurez-vous que ces codes à gauche sont EXACTEMENT ceux écrits dans votre fichier CSV
SKU_MAPPING = {
    "MAGOSL12": "GOSE LIME 3.9%",
    "MAMEXL12": "MEXICAINE LIME 4.5%",
    "MARADC12": "RADLER CLEMENTINE 3.5%"
}
SKU_ORDER = ["GOSE LIME 3.9%", "MEXICAINE LIME 4.5%", "RADLER CLEMENTINE 3.5%"]

st.title("🍹 Diagnostic des Ventes : Radler & Gose")

uploaded_file = st.file_uploader("Glissez le fichier CSV ici", type="csv")

if uploaded_file:
    try:
        # 1. Lecture brute pour détecter le séparateur (virgule ou point-virgule)
        raw_data = uploaded_file.getvalue().decode('latin1')
        sep = ';' if ';' in raw_data.split('\n')[0] else ','
        uploaded_file.seek(0)
        
        df = pd.read_csv(uploaded_file, encoding='latin1', sep=sep)
        
        # 2. Nettoyage des noms de colonnes
        df.columns = df.columns.str.strip()

        # 3. Diagnostic Immédiat
        st.subheader("📊 État du fichier")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Nombre de transactions", len(df))
        
        # 4. Nettoyage des colonnes numériques
        for col in ['LineQty', 'LineTotal', 'Rabais']:
            if col in df.columns:
                # On transforme en texte, enlève les espaces, change la virgule en point
                df[col] = df[col].astype(str).str.replace(r'[^\d,.-]', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        with col2:
            st.metric("Total Caisses (LineQty)", f"{df['LineQty'].sum() if 'LineQty' in df.columns else 0}")

        # 5. Mapping et détection des codes
        df['ItemCode_Clean'] = df['ItemCode'].astype(str).str.strip()
        df['Nom_Propre'] = df['ItemCode_Clean'].map(SKU_MAPPING)

        with col3:
            trouves = df['Nom_Propre'].notna().sum()
            st.metric("Ventes reconnues (Mapping)", trouves)

        # 6. Affichage des codes non reconnus pour vous aider
        if trouves == 0 and len(df) > 0:
            st.warning("⚠️ Aucun code ItemCode du fichier ne correspond à votre liste.")
            st.write("Codes trouvés dans votre fichier :", df['ItemCode_Clean'].unique().tolist())
            st.write("Codes attendus par l'app :", list(SKU_MAPPING.keys()))

        # 7. Création des rapports
        def force_order(data_df):
            base = pd.DataFrame({'Nom_Propre': SKU_ORDER})
            merged = pd.merge(base, data_df, on='Nom_Propre', how='left').fillna(0)
            return merged.rename(columns={'Nom_Propre': 'ItemName'})

        res_sku = force_order(df.groupby('Nom_Propre')['LineQty'].sum().reset_index())
        res_jour = force_order(df.pivot_table(index='Nom_Propre', columns='DocDate', values='LineQty', aggfunc='sum', fill_value=0).reset_index())
        res_fin = force_order(df.groupby('Nom_Propre').agg({'LineTotal': 'sum', 'Rabais': 'sum'}).reset_index())

        # 8. Aperçu et Téléchargement
        st.divider()
        st.subheader("👀 Aperçu des résultats")
        st.dataframe(res_sku)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_sku.to_excel(writer, sheet_name='SKU_Caisses', index=False)
            res_jour.to_excel(writer, sheet_name='SKU_Par_Jour', index=False)
            res_fin.to_excel(writer, sheet_name='SKU_Financier', index=False)

        st.download_button("📥 Télécharger l'Excel", output.getvalue(), "Ventes_Radler_Gose.xlsx")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
