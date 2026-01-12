import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Radler & Gose - Convertisseur", layout="wide")

# --- LISTE DES SKUS (ORDRE FIXE DEMANDÉ) ---
# Note : Les codes items sont basés sur votre nomenclature habituelle
SKU_MAPPING = {
    "MAGOSL12": "GOSE LIME 3.9%",
    "MAMEXL12": "MEXICAINE LIME 4.5%",
    "MARADC12": "RADLER CLEMENTINE 3.5%"
}

SKU_ORDER = ["GOSE LIME 3.9%", "MEXICAINE LIME 4.5%", "RADLER CLEMENTINE 3.5%"]

st.title("🍹 Extracteur : Gamme Radler & Gose")
st.info("Utilisez cette application pour les fichiers de type F002783.")

uploaded_file = st.file_uploader("Glissez le fichier CSV ici", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='latin1')
        
        # Nettoyage numérique
        for col in ['LineQty', 'LineTotal', 'Rabais']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # Mapping des noms propres
        df['Nom_Propre'] = df['ItemCode'].map(SKU_MAPPING).fillna(df['ItemName'])

        def force_order(data_df):
            # On crée le squelette avec l'ordre exact
            base = pd.DataFrame({'Nom_Propre': SKU_ORDER})
            merged = pd.merge(base, data_df, on='Nom_Propre', how='left').fillna(0)
            return merged.rename(columns={'Nom_Propre': 'ItemName'})

        # Préparation des DataFrames
        data_sheets = {
            'SKU_Caisses': force_order(df.groupby('Nom_Propre')['LineQty'].sum().reset_index()),
            'SKU_Par_Jour': force_order(df.pivot_table(index='Nom_Propre', columns='DocDate', values='LineQty', aggfunc='sum', fill_value=0).reset_index()),
            'Banniere_Caisses': df.groupby('GroupName')['LineQty'].sum().sort_values(ascending=False).reset_index(),
            'Region_Caisses': df.groupby('CityS')['LineQty'].sum().sort_values(ascending=False).reset_index(),
            'Rep_Caisses': df.groupby('RefPartenaire')['LineQty'].sum().sort_values(ascending=False).reset_index(),
            'SKU_Financier': force_order(df.groupby('Nom_Propre').agg({'LineTotal': 'sum', 'Rabais': 'sum'}).reset_index())
        }

        # Export Excel avec mise en page
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet_name, data in data_sheets.items():
                data.to_excel(writer, sheet_name=sheet_name, index=False)
                worksheet = writer.sheets[sheet_name]
                workbook = writer.book
                header_format = workbook.add_format({'bold': True, 'bg_color': '#FFCC99', 'border': 1}) # Couleur orange pour différencier
                
                for i, col in enumerate(data.columns):
                    column_len = max(data[col].astype(str).str.len().max(), len(col)) + 2
                    worksheet.set_column(i, i, column_len)
                    worksheet.write(0, i, col, header_format)

        st.success("✅ Fichier Radler/Gose traité !")
        st.download_button("📥 Télécharger Excel", output.getvalue(), "Ventes_Radler_Gose.xlsx")

    except Exception as e:
        st.error(f"Une erreur est survenue : {e}")
