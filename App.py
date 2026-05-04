import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time
import os

# 1. Opsætning af siden
st.set_page_config(page_title="Fantasy Fodbold Stats", page_icon="⚽", layout="wide")
st.title("🏆 Vores Fantasy Liga Dashboard")

# 2. Indlæs og flet data
@st.cache_data
def load_data():
    try:
        D_point = pd.read_csv("Data_point.csv")
        D_chips = pd.read_csv("Data_chips.csv")

        # --- FIX 1: Holdværdi konvertering ---
        # Hvis værdierne er over 200 (f.eks. 1014), så er de i tusinder og divideres med 10
        if 'Værdi' in D_point.columns and D_point['Værdi'].mean() > 200:
            D_point['Værdi'] = D_point['Værdi'] / 10

        # --- FIX 2: Sikker oversættelse af chips (fx triple_1 og wildcard_2) ---
        id_vars = ['Entry id', 'Navn', 'Holdnavn']
        chip_cols = [col for col in D_chips.columns if col not in id_vars and "Unnamed" not in col]
        
        # Vend dataen om, så vi kan læse den
        D_chips_long = D_chips.melt(id_vars=id_vars, value_vars=chip_cols, var_name='Rå_Chip', value_name='GW')
        
        # Sikr at GW er et tal, og fjern fejl eller nuller fra gamle u-brugte chips
        D_chips_long['GW'] = pd.to_numeric(D_chips_long['GW'], errors='coerce')
        D_chips_long = D_chips_long.dropna(subset=['GW'])
        D_chips_long = D_chips_long[D_chips_long['GW'] > 0] # Fjerner chips sat til GW 0
        D_chips_long['GW'] = D_chips_long['GW'].astype(int)
        
        # Funktion der fjerner "_1", "_2" og giver dem de rigtige FPL-navne
        def rens_chip_navn(c):
            c = str(c).lower()
            if 'wildcard' in c: return 'Wildcard'
            if 'triple' in c or '3xc' in c: return 'Triple Captain'
            if 'bboost' in c or 'bench' in c: return 'Bench Boost'
            if 'free' in c or 'hit' in c: return 'Free Hit'
            if 'manager' in c: return 'Ass. Manager'
            import re
            return re.sub(r'(_|\s)\d+', '', c).title() # Fallback der bare fjerner tal
            
        D_chips_long['Chip'] = D_chips_long['Rå_Chip'].apply(rens_chip_navn)
        
        # Slå chips sammen per gameweek (så vi er sikre på der ikke sker dublet-fejl i merge)
        chips_grouped = D_chips_long.groupby(['Entry id', 'GW'])['Chip'].apply(lambda x: ' & '.join(x.unique())).reset_index()
        
        # --- Flet det hele sammen ---
        D_point['GW'] = D_point['GW'].astype(int)
        D = pd.merge(D_point, chips_grouped, on=['Entry id', 'GW'], how='left')
        D['Chip'] = D['Chip'].fillna("")
        
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
        
        # --- BILLEDE OG STATS LAYOUT ---
        col_img, col_stats = st.columns([1, 3])
        
        with col_img:
            billed_sti = f"{valgt_manager}.jpg"
            if os.path.exists(billed_sti):
                st.image(billed_sti, use_column_width=True)
            else:
                st.info(f"Mangler billede på GitHub: {valgt_manager}.jpg")
                
        with col_stats:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Totale Effektive Point", df["Effektive point"].sum())
            col2.metric("Højeste GW Score", df["Effektive point"].max())
            col3.metric("Chips Brugt", len(df[df["Chip"] != ""]))
            
            if len(df) >= 3:
                form_point = df.tail(3)["Effektive point"].sum()
                col4.metric("🔥 Form (Seneste 3 runder)", form_point)
            else:
                col4.metric("🔥 Form", "Ikke nok runder")

        st.divider()

        # --- GRAFER ---
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Point pr. Gameweek")
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(df["GW"], df["Effektive point"], color="skyblue", label="Point")

            chip_gw = df[df["Chip"] != ""]
            ax.scatter(chip_gw["GW"], chip_gw["Effektive point"] + 1.5,
                        color="red", marker="*", s=200, label="Chip spillet")

            for _, row in chip_gw.iterrows():
                ax.text(row["GW"], row["Effektive point"] + 3, row["Chip"],
                         ha='center', va='bottom', fontsize=9, rotation=45)

            ax.set_xlabel("Gameweek")
            ax.set_ylabel("Point")
            max_gw = int(D["GW"].max()) if not D.empty else 38
            ax.set_xticks(range(1, max_gw + 1)) 
            ax.grid(axis='y', linestyle='--', alpha=0.7)
            st.pyplot(fig)
            
        with col_graf2:
            st.subheader("💰 Holdværdi over tid")
            fig2, ax2 = plt.subplots(figsize=(10, 5))
            ax2.plot(df["GW"], df["Værdi"], color="green", marker="o", linewidth=2)
            ax2.set_xlabel("Gameweek")
            ax2.set_ylabel("Værdi (Mio.)")
            ax2.set_xticks(range(1, max_gw + 1)) 
            ax2.grid(True, linestyle='--', alpha=0.7)
            st.pyplot(fig2)

        st.subheader("Rå data")
        st.dataframe(df, use_container_width=True)

    # ==========================================
    # FANE 2: LIGA OVERSIGT
    # ==========================================
    with tab2:
        st.header("🌍 Generelle Liga Statistikker")
        
        # --- FIND REKORDER ---
        bedste_gw = D.loc[D['Effektive point'].idxmax()]
        værste_gw = D.loc[D['Effektive point'].idxmin()]
        bedste_bænk = D.loc[D['Point på bænk'].idxmax()]
        
        hit_mager_navn = D.groupby('Navn')['Transfers minuspoint'].sum().idxmax()
        hit_mager_point = D.groupby('Navn')['Transfers minuspoint'].sum().max()
        
        max_gw = D['GW'].max()
        rigeste_manager = D[D['GW'] == max_gw].sort_values('Værdi', ascending=False).iloc[0]
        
        if max_gw >= 3:
            seneste_3_data = D[D['GW'] > max_gw - 3]
            form_stats = seneste_3_data.groupby('Navn')['Effektive point'].sum().reset_index()
            form_konge = form_stats.loc[form_stats['Effektive point'].idxmax()]
        
        # --- VIS REKORDER ---
        col1, col2, col3 = st.columns(3)
        col1.metric("🏆 Højeste GW Score", f"{bedste_gw['Effektive point']} point", f"{bedste_gw['Navn']} (GW {int(bedste_gw['GW'])})", delta_color="off")
        col2.metric("📉 Laveste GW Score", f"{værste_gw['Effektive point']} point", f"{værste_gw['Navn']} (GW {int(værste_gw['GW'])})", delta_color="off")
        col3.metric("🪑 Bænk-brøleren", f"{bedste_bænk['Point på bænk']} point", f"{bedste_bænk['Navn']} (GW {int(bedste_bænk['GW'])})", delta_color="inverse")

        st.write("") 
        
        col4, col5, col6 = st.columns(3)
        col4.metric("✂️ Hit-mageren", f"-{hit_mager_point} point", f"{hit_mager_navn}", delta_color="inverse")
        col5.metric("💰 Holdværdi-kongen", f"{rigeste_manager['Værdi']} mio.", f"{rigeste_manager['Navn']} (Nu)", delta_color="off")
        if max_gw >= 3:
            col6.metric("🔥 Form-kongen", f"{form_konge['Effektive point']} point", f"{form_konge['Navn']} (Seneste 3)", delta_color="off")

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
                time.sleep(0.1) 
        
        st.divider()
        
        # --- GENNEMSNITLIGE STATS ---
        st.subheader("📊 Gennemsnitlige Stats pr. Manager")
        
        avg_stats = D.groupby('Navn').agg(
            Gns_point_pr_runde=('Effektive point', 'mean'),
            Gns_point_på_bænken=('Point på bænk', 'mean'),
            Transfers_i_alt=('Transfers', 'sum'),
            Transfer_minuspoint=('Transfers minuspoint', 'sum')
        ).round(1).reset_index()
        
        avg_stats.columns = ['Navn', 'Gns. point pr. runde', 'Gns. point på bænken', 'Transfers i alt', 'Transfer minuspoint']
        avg_stats = avg_stats.sort_values(by="Gns. point pr. runde", ascending=False)
        avg_stats.index = range(1, len(avg_stats) + 1)
        
        st.dataframe(avg_stats, use_container_width=True)
