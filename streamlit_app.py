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

        # 4. Mapping
        df['ItemCode_Clean'] = df['ItemCode'].astype(str).str.strip()
        df['Nom_Propre'] = df['ItemCode_Clean'].map(SKU_MAPPING)

        # 5. Fonction pour forcer l'ordre et ajouter le Total
        def force_order(data_df):
            base = pd.DataFrame({'Nom_Propre': SKU_ORDER})
            merged = pd.merge(base, data_df, on='Nom_Propre', how='left').fillna(0)
            
            if not merged.empty:
                numeric_cols = merged.select_dtypes(include=['number']).columns
                total_row = merged[numeric_cols].sum()
                total_df = pd.DataFrame([total_row], columns=numeric_cols)
                total_df['Nom_Propre'] = 'TOTAL GÉNÉRAL'
                merged = pd.concat([merged, total_df], ignore_index=True)
            
            return merged.rename(columns={'Nom_Propre': 'ItemName'})

        # 6. Calculs des onglets
        res_sku = force_order(df.groupby('Nom_Propre')['LineQty'].sum().reset_index())
        
        if 'DocDate' in df.columns:
            res_jour = df.pivot_table(index='Nom_Propre', columns='DocDate', values='LineQty', aggfunc='sum', fill_value=0).reset_index()
            res_jour = force_order(res_jour)
        else:
            res_jour = pd.DataFrame({"Message": ["DocDate manquante"]})

        res_fin = df.groupby('Nom_Propre').agg({'LineTotal': 'sum', 'Rabais': 'sum'}).reset_index()
        res_fin = force_order(res_fin)

        res_banniere = df.groupby('GroupName')['LineQty'].sum().sort_values(ascending=False).reset_index()
        res_region = df.groupby('CityS')['LineQty'].sum().sort_values(ascending=False).reset_index()
        res_rep = df.groupby('RefPartenaire')['LineQty'].sum().sort_values(ascending=False).reset_index()

        # --- AFFICHAGE ET EXPORT ---
        st.subheader("👀 Aperçu des résultats")
        st.dataframe(res_sku, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_sku.to_excel(writer, sheet_name='SKU_Caisses', index=False)
            res_jour.to_excel(writer, sheet_name='SKU_Par_Jour', index=False)
            res_banniere.to_excel(writer, sheet_name='Banniere', index=False)
            res_region.to_excel(writer, sheet_name='Region', index=False)
            res_rep.to_excel(writer, sheet_name='Representant', index=False)
            res_fin.to_excel(writer, sheet_name='Financier', index=False)
            
            for sheet in writer.sheets:
                writer.sheets[sheet].set_column(0, 0, 35)

        st.download_button("📥 Télécharger le rapport Excel", output.getvalue(), "Ventes_Radler_Gose_Final.xlsx")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
