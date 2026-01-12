import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Radler & Gose - Diagnostic", layout="wide")

SKU_MAPPING = {
    "MAGOSL12": "GOSE LIME 3.9%",
    "MAMEXL12": "MEXICAINE LIME 4.5%",
    "MARADC12": "RADLER CLEMENTINE 3.5%"
}
SKU_ORDER = ["GOSE LIME 3.9%", "MEXICAINE LIME 4.5%", "RADLER CLEMENTINE 3.5%"]

st.title("🍹 Diagnostic d'importation : Radler & Gose")

uploaded_file = st.file_uploader("Glissez le fichier CSV ici", type="csv")

if uploaded_file:
    try:
        # --- ETAPE 1 : DETECTION DU SEPARATEUR ---
        # On lit la première ligne pour voir si elle contient des ; ou des ,
        first_line = uploaded_file.getvalue().decode('latin1').split('\n')[0]
        separator = ';' if ';' in first_line else ','
        
        # Réinitialiser le pointeur du fichier après la lecture de la première ligne
        uploaded_file.seek(0)
        
        # Lecture du fichier avec le bon séparateur
        df = pd.read_csv(uploaded_file, encoding='latin1', sep=separator)
        
        # --- ETAPE 2 : NETTOYAGE ---
        df.columns = df.columns.str.strip() # Enlever les espaces dans les titres
        
        # Nettoyage des chiffres (virgules -> points)
        for col in ['LineQty', 'LineTotal', 'Rabais']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(' ', '', regex=False)
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Mapping
        df['Nom_Propre'] = df['ItemCode'].astype(str).str.strip().map(SKU_MAPPING).fillna(df['ItemName'])

        # --- ETAPE 3 : TABLEAU DE BORD DE VERIFICATION ---
        st.subheader("🔍 Ce que l'application voit :")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Lignes détectées", len(df))
        with col2:
            st.metric("Total Quantité (LineQty)", f"{df['LineQty'].sum()} caisses")
        with col3:
            st.metric("Séparateur utilisé", f"'{separator}'")

        if st.checkbox("Voir un aperçu des données brutes lues"):
            st.write(df[['ItemCode', 'ItemName', 'LineQty']].head(10))

        # --- ETAPE 4 : CALCULS ET EXPORT ---
        def force_order(data_df):
            base = pd.DataFrame({'Nom_Propre': SKU_ORDER})
            merged = pd.merge(base, data_df, on='Nom_Propre', how='left').fillna(0)
            return merged.rename(columns={'Nom_Propre': 'ItemName'})

        res_sku = force_order(df.groupby('Nom_Propre')['LineQty'].sum().reset_index())
        res_jour = force_order(df.pivot_table(index='Nom_Propre', columns='DocDate', values='LineQty', aggfunc='sum', fill_value=0).reset_index())
        res_fin = force_order(df.groupby('Nom_Propre').agg({'LineTotal': 'sum', 'Rabais': 'sum'}).reset_index())

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_sku.to_excel(writer, sheet_name='SKU_Caisses', index=False)
            res_jour.to_excel(writer, sheet_name='SKU_Par_Jour', index=False)
            res_fin.to_excel(writer, sheet_name='SKU_Financier', index=False)

        st.divider()
        st.download_button("📥 Télécharger l'Excel", output.getvalue(), "Ventes_Radler_Gose.xlsx")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
