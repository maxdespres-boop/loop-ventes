import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Radler & Gose - Diagnostic", layout="wide")

# Liste de mapping
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
        # 1. Lecture brute pour détecter le séparateur
        content = uploaded_file.getvalue().decode('latin1')
        sep = ';' if ';' in content.split('\n')[0] else ','
        uploaded_file.seek(0)
        
        # 2. Chargement du DataFrame
        df = pd.read_csv(uploaded_file, encoding='latin1', sep=sep)
        
        # 3. Nettoyage immédiat des noms de colonnes (enlève espaces et retours à la ligne)
        df.columns = df.columns.str.strip()

        # 4. Conversion forcée des colonnes numériques
        # On enlève TOUT ce qui n'est pas un chiffre, une virgule ou un point
        for col in ['LineQty', 'LineTotal', 'Rabais']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'[^\d,.-]', '', regex=True)
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 5. Diagnostic visuel pour vous aider
        st.subheader("📊 Rapport de diagnostic")
        d_col1, d_col2, d_col3 = st.columns(3)
        
        with d_col1:
            st.metric("Lignes trouvées", len(df))
            st.write("Colonnes détectées :", list(df.columns))
            
        with d_col2:
            qty_total = df['LineQty'].sum() if 'LineQty' in df.columns else "N/A"
            st.metric("Total LineQty", qty_total)
            
        with d_col3:
            # Vérification des codes items
            codes_trouves = df['ItemCode'].unique() if 'ItemCode' in df.columns else []
            st.write(f"Codes items uniques trouvés ({len(codes_trouves)}) :")
            st.write(codes_trouves)

        # 6. Traitement des données
        df['Nom_Propre'] = df['ItemCode'].astype(str).str.strip().map(SKU_MAPPING)

        def force_order(data_df):
            base = pd.DataFrame({'Nom_Propre': SKU_ORDER})
            merged = pd.merge(base, data_df, on='Nom_Propre', how='left').fillna(0)
            return merged.rename(columns={'Nom_Propre': 'ItemName'})

        # Groupements
        res_sku = force_order(df.groupby('Nom_Propre')['LineQty'].sum().reset_index())
        res_jour = force_order(df.pivot_table(index='Nom_Propre', columns='DocDate', values='LineQty', aggfunc='sum', fill_value=0).reset_index())
        res_fin = force_order(df.groupby('Nom_Propre').agg({'LineTotal': 'sum', 'Rabais': 'sum'}).reset_index())

        # Aperçu des résultats
        st.divider()
        st.subheader("👀 Aperçu du résultat SKU_Caisses")
        st.table(res_sku)

        # Export Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_sku.to_excel(writer, sheet_name='SKU_Caisses', index=False)
            res_jour.to_excel(writer, sheet_name='SKU_Par_Jour', index=False)
            res_fin.to_excel(writer, sheet_name='SKU_Financier', index=False)

        st.download_button("📥 Télécharger l'Excel", output.getvalue(), "Ventes_Radler_Gose.xlsx")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
