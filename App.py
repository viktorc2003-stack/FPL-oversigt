import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time

# 1. Opsætning af siden
st.set_page_config(page_title="Fantasy Fodbold Stats", page_icon="⚽", layout="wide")
st.title("🏆 Vores Fantasy Liga Dashboard")

# 2. Indlæs og flet data
@st.cache_data
def load_data():
    try:
        D_point = pd.read_csv("Data_point.csv")
        D_chips = pd.read_csv("Data_chips.csv")

        id_vars = ['Entry id', 'Navn', 'Holdnavn']
        chip_cols = [col for col in D_chips.columns if col not in id_vars and "Unnamed" not in col]
        
        D_chips_long = D_chips.melt(id_vars=id_vars, value_vars=chip_cols, var_name='Chip', value_name='GW')
        D_chips_long = D_chips_long.dropna(subset=['GW'])
        
        D = pd.merge(D_point, D_chips_long[['Entry id', 'GW', 'Chip']], on=['Entry id', 'GW'], how='left')
        
        # --- RENS SKRIFTEN (Fjerner underscores fra chips) ---
        D['Chip'] = D['Chip'].fillna("").str.replace('_', ' ').str.title()
        
        return D
        
    except FileNotFoundError as e:
        st.error(f"Kunne ikke finde filerne. Fejl: {e}")
        return pd.DataFrame()

D = load_data()

if not D.empty:
    
    # --- OPRET FANER (TABS) ---
    tab1, tab2 = st.tabs(["👤 Individuel Manager", "🌍 Liga Oversigt"])
    
    # ==========================================
    # FANE 1: INDIVIDUEL MANAGER
    # ==========================================
    with tab1:
        st.sidebar.header("Indstillinger")
        managere = D["Navn"].unique()
        valgt_manager = st.sidebar.selectbox("Vælg en Manager:", managere)

        df = D[D["Navn"] == valgt_manager].sort_values("GW")

        st.header(f"Statistik for {valgt_manager}")
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Totale Effektive Point", df["Effektive point"].sum())
        col2.metric("Højeste GW Score", df["Effektive point"].max())
        col3.metric("Chips Brugt", len(df[df["Chip"] != ""]))

        st.divider()

        st.subheader("Point pr. Gameweek")
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.bar(df["GW"], df["Effektive point"], color="skyblue", label="Point")

        chip_gw = df[df["Chip"] != ""]
        ax.scatter(chip_gw["GW"], chip_gw["Effektive point"] + 1.5,
                    color="red", marker="*", s=200, label="Chip spillet")

        for _, row in chip_gw.iterrows():
            ax.text(row["GW"], row["Effektive point"] + 3, row["Chip"],
                     ha='center', va='bottom', fontsize=9, rotation=45)

        ax.set_title(f"{valgt_manager} – Point pr. Gameweek")
        ax.set_xlabel("Gameweek")
        ax.set_ylabel("Point")
        
        max_gw = int(D["GW"].max()) if not D.empty else 38
        ax.set_xticks(range(1, max_gw + 1)) 
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        st.pyplot(fig)

        st.subheader("Rå data")
        st.dataframe(df)

    # ==========================================
    # FANE 2: LIGA OVERSIGT
    # ==========================================
    with tab2:
        st.header("🌍 Generelle Liga Statistikker")
        
        # --- FIND REKORDER ---
        bedste_gw = D.loc[D['Effektive point'].idxmax()]
        værste_gw = D.loc[D['Effektive point'].idxmin()]
        bedste_bænk = D.loc[D['Point på bænk'].idxmax()]
        
        col1, col2, col3 = st.columns(3)
        
        col1.metric(label="🏆 Højeste GW Score", 
                    value=f"{bedste_gw['Effektive point']} point", 
                    delta=f"{bedste_gw['Navn']} (GW {int(bedste_gw['GW'])})", delta_color="off")
        
        col2.metric(label="📉 Laveste GW Score", 
                    value=f"{værste_gw['Effektive point']} point", 
                    delta=f"{værste_gw['Navn']} (GW {int(værste_gw['GW'])})", delta_color="off")
        
        col3.metric(label="🪑 Flest point på bænken", 
                    value=f"{bedste_bænk['Point på bænk']} point", 
                    delta=f"{bedste_bænk['Navn']} (GW {int(bedste_bænk['GW'])})", delta_color="off")

        st.divider()

        # --- ANIMERET POSITION SGRAF ---
        st.subheader("🎬 Animeret Sæsonudvikling")
        
        if st.button("▶️ Afspil sæsonen"):
            graf_boks = st.empty() 
            max_gw_spillet = int(D["GW"].max())
            
            for nuværende_gw in range(1, max_gw_spillet + 1):
                fig3, ax3 = plt.subplots(figsize=(14, 6))
                temp_D = D[D["GW"] <= nuværende_gw]
                
                for navn in managere:
                    manager_data = temp_D[temp_D['Navn'] == navn].sort_values('GW')
                    ax3.plot(manager_data['GW'], manager_data['Position'], 'o-', markersize=4, label=navn)

                ax3.invert_yaxis() 
                ax3.set_ylim(len(managere) + 0.5, 0.5) 
                ax3.set_xlim(1, max_gw_spillet if max_gw_spillet > 1 else 38)
                ax3.grid(True, linestyle='--', alpha=0.6)
                ax3.set_xlabel("Gameweek")
                ax3.set_ylabel("Position")
                ax3.set_title(f"Ligastilling efter Gameweek {nuværende_gw}")
                ax3.legend(loc='upper left', bbox_to_anchor=(1, 1))
                
                graf_boks.pyplot(fig3)
                plt.close(fig3)
                time.sleep(0.1) # HURTIGERE HASTIGHED
        
        st.divider()
        
        # --- GENNEMSNITLIGE STATS (Renset for underscores) ---
        st.subheader("📊 Gennemsnitlige Stats pr. Manager")
        
        avg_stats = D.groupby('Navn').agg(
            Gns_point_pr_runde=('Effektive point', 'mean'),
            Gns_point_på_bænken=('Point på bænk', 'mean'),
            Transfers_i_alt=('Transfers', 'sum'),
            Transfer_minuspoint=('Transfers minuspoint', 'sum')
        ).round(1).reset_index()
        
        # Omdøb kolonnerne så de ser pæne ud i tabellen
        avg_stats.columns = ['Navn', 'Gns. point pr. runde', 'Gns. point på bænken', 'Transfers i alt', 'Transfer minuspoint']
        
        avg_stats = avg_stats.sort_values(by="Gns. point pr. runde", ascending=False)
        avg_stats.index = range(1, len(avg_stats) + 1)
        
        st.dataframe(avg_stats, use_container_width=True)