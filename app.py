import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import kagglehub
from kagglehub import KaggleDatasetAdapter

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="E-commerce Pro Analytics", layout="wide")

# --- 2. STYLE CSS (Thème Sombre Premium) ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .kpi-card {
        background-color: #1E293B; padding: 20px; border-radius: 12px;
        border: 1px solid #334155; margin-bottom: 10px;
    }
    .kpi-label { color: #94A3B8; font-size: 0.85rem; margin-bottom: 5px; }
    .kpi-value { color: #FFFFFF; font-size: 1.6rem; font-weight: 700; }
    .up { color: #10B981; font-weight: 600; font-size: 0.8rem; }
    .down { color: #F43F5E; font-weight: 600; font-size: 0.8rem; }
    .neutral { color: #64748B; font-weight: 600; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# --- 3. PIPELINE DE DONNÉES AUTOMATIQUE ---
@st.cache_data(show_spinner="Récupération et analyse des données Kaggle...")
def load_and_process_data():
    # Téléchargement avec correction de l'encodage
    df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        "carrie1/ecommerce-data",
        "data.csv",
        pandas_kwargs={'encoding': 'ISO-8859-1'}
    )

    # Nettoyage
    df.dropna(subset=["CustomerID"], inplace=True)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["UnitPrice"] = df["UnitPrice"].astype(float)
    df['TotalRevenue'] = df['Quantity'] * df['UnitPrice']
    df['IsCancelled'] = df['InvoiceNo'].str.startswith('C', na=False)

    # Enrichissement temporel
    df['Month'] = df['InvoiceDate'].dt.to_period('M')
    df['Year'] = df['InvoiceDate'].dt.year
    df['Date'] = df['InvoiceDate'].dt.date

    # Mapping Géographique Complet
    COUNTRY_TO_CONTINENT = {
        'United Kingdom': 'Europe', 'France': 'Europe', 'Germany': 'Europe', 'EIRE': 'Europe',
        'Spain': 'Europe', 'Netherlands': 'Europe', 'Belgium': 'Europe', 'Switzerland': 'Europe',
        'Portugal': 'Europe', 'Norway': 'Europe', 'Italy': 'Europe', 'Channel Islands': 'Europe',
        'Finland': 'Europe', 'Cyprus': 'Europe', 'Sweden': 'Europe', 'Austria': 'Europe',
        'Poland': 'Europe', 'Denmark': 'Europe', 'Greece': 'Europe', 'Malta': 'Europe',
        'Lithuania': 'Europe', 'Iceland': 'Europe', 'Czech Republic': 'Europe', 
        'European Community': 'Europe', 'USA': 'Amériques', 'Canada': 'Amériques', 
        'Brazil': 'Amériques', 'Japan': 'Asie', 'Singapore': 'Asie', 'Israel': 'Asie', 
        'United Arab Emirates': 'Asie', 'Bahrain': 'Asie', 'Lebanon': 'Asie', 
        'Saudi Arabia': 'Asie', 'Hong Kong': 'Asie', 'Australia': 'Océanie', 
        'RSA': 'Afrique', 'Unspecified': 'Non Spécifié'
    }
    df['Continent'] = df['Country'].map(COUNTRY_TO_CONTINENT).fillna('Europe')
    return df

df_raw = load_and_process_data()

# --- 4. SIDEBAR (FILTRES) ---
st.sidebar.header("📍 Géographie")
all_continents = sorted(df_raw['Continent'].unique().tolist())
sel_continents = st.sidebar.multiselect("Continents", options=all_continents, default=all_continents)

avail_countries = sorted(df_raw[df_raw['Continent'].isin(sel_continents)]['Country'].unique().tolist())
sel_countries = st.sidebar.multiselect("Pays", options=avail_countries, default=avail_countries)

st.sidebar.divider()
st.sidebar.header("📅 Temporalité")
time_option = st.sidebar.selectbox("Période", ["Mois actuel", "Année en cours", "Toute la durée"])

# --- 5. LOGIQUE TEMPORELLE ---
max_date = df_raw['InvoiceDate'].max()
curr_m, curr_y = max_date.to_period('M'), max_date.year

if time_option == "Mois actuel":
    df_p = df_raw[df_raw['Month'] == curr_m]
    df_prev = df_raw[df_raw['Month'] == (curr_m - 1)]
    g_col, comp_label = 'Date', "vs mois dernier"
elif time_option == "Année en cours":
    df_p = df_raw[df_raw['Year'] == curr_y]
    df_prev = df_raw[df_raw['Year'] == (curr_y - 1)]
    g_col, comp_label = 'Month', "vs an dernier"
else:
    df_p, df_prev = df_raw, pd.DataFrame()
    g_col, comp_label = 'Month', ""

df = df_p[df_p['Country'].isin(sel_countries)]
df_c = df_prev[df_prev['Country'].isin(sel_countries)] if not df_prev.empty else pd.DataFrame()

# --- 6. CALCULS KPIs ---
def stats(d):
    if d.empty: return 0, 0, 0, 0, 0
    r = d[d['TotalRevenue'] > 0]['TotalRevenue'].sum()
    o = d['InvoiceNo'].nunique()
    c = d['CustomerID'].nunique()
    l = abs(d[d['TotalRevenue'] < 0]['TotalRevenue'].sum())
    return r, o, c, (r/o if o>0 else 0), l

sc = stats(df)
sp = stats(df_c)
def delta(curr, prev): return ((curr - prev) / prev * 100) if prev > 0 else 0

# --- 7. INTERFACE PAR ONGLETS ---
st.title("🚀 Business Analytics Dashboard")
tab_global, tab_client = st.tabs(["📊 Vue Globale", "👥 Vue Client"])

# ==========================================
# ONGLET 1 : VUE GLOBALE
# ==========================================
with tab_global:
    # ROW 1: KPIs
    cols = st.columns(5)
    names = ["Revenue", "Commandes", "Clients", "Panier Moyen", "Pertes (Annul.)"]
    for i, col in enumerate(cols):
        val = sc[i]
        d = delta(sc[i], sp[i])
        color = "up" if (d >= 0 if i != 4 else d <= 0) else "down"
        if d == 0: color = "neutral"
        col.markdown(f"""<div class="kpi-card"><div class="kpi-label">{names[i]}</div><div class="kpi-value">{val:,.0f}{' €' if i in [0,3,4] else ''}</div>
        <div class="{color}">{"↑" if d>0 else "↓" if d<0 else "→"} {abs(d):.1f}% <span style="color:#64748B">{comp_label}</span></div></div>""", unsafe_allow_html=True)

    # ROW 2: Tendance & Pie Chart
    st.write("##")
    c_l, c_r = st.columns([2, 1])
    with c_l:
        st.subheader("📈 Dynamique du CA Net")
        if not df.empty:
            net_data = df.groupby(g_col)['TotalRevenue'].sum().reset_index()
            if g_col == 'Month': net_data['Month'] = net_data['Month'].astype(str)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=net_data[g_col], y=net_data['TotalRevenue'].clip(lower=0), mode='lines', fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.3)', line=dict(color='#10B981'), name='Profit'))
            fig.add_trace(go.Scatter(x=net_data[g_col], y=net_data['TotalRevenue'].clip(upper=0), mode='lines', fill='tozeroy', fillcolor='rgba(244, 63, 94, 0.3)', line=dict(color='#F43F5E'), name='Perte'))
            fig.update_layout(template="plotly_dark", hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with c_r:
        st.subheader("🌍 Part des Pays")
        if not df.empty:
            geo = df.groupby('Country')['InvoiceNo'].nunique().reset_index().sort_values('InvoiceNo', ascending=False)
            plot_df = geo if (len(sel_continents) == 1 and len(geo) <= 7) else pd.concat([geo.head(5), pd.DataFrame({'Country': ['Autres'], 'InvoiceNo': [geo.iloc[5:]['InvoiceNo'].sum()]})])
            st.plotly_chart(px.pie(plot_df, values='InvoiceNo', names='Country', hole=0.5, template="plotly_dark").update_traces(textinfo='percent+label').update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0,b=0,l=0,r=0)), use_container_width=True)

    # ROW 3: Produits
    st.write("##")
    r3l, r3r = st.columns(2)
    with r3l:
        st.subheader("🏆 Top 10 Vendus")
        top_v = df[df['Quantity'] > 0].groupby('Description')['Quantity'].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(top_v, x='Quantity', y='Description', orientation='h', template="plotly_dark", color_discrete_sequence=['#818CF8']).update_layout(yaxis={'categoryorder':'total ascending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with r3r:
        st.subheader("🚫 Top 10 Annulés")
        top_r = df[df['Quantity'] < 0].groupby('Description')['Quantity'].sum().abs().nlargest(10).reset_index()
        st.plotly_chart(px.bar(top_r, x='Quantity', y='Description', orientation='h', template="plotly_dark", color_discrete_sequence=['#F43F5E']).update_layout(yaxis={'categoryorder':'total ascending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'), use_container_width=True)

# ==========================================
# ONGLET 2 : VUE CLIENT
# ==========================================
with tab_client:
    if not df.empty:
        st.subheader("💎 Analyse Client")
        client_stats = df.groupby('CustomerID').agg({'InvoiceNo': 'nunique', 'TotalRevenue': 'sum'}).reset_index()
        
        # Calcul du Score Net demandé (Revenue - Nombre de retours)
        returns_count = df[df['TotalRevenue'] < 0].groupby('CustomerID')['InvoiceNo'].nunique().reset_index()
        returns_count.columns = ['CustomerID', 'NbRetours']
        client_stats = pd.merge(client_stats, returns_count, on='CustomerID', how='left').fillna(0)
        client_stats['ScoreNet'] = client_stats['TotalRevenue'] - client_stats['NbRetours']
        
        best = client_stats.nlargest(1, 'InvoiceNo').iloc[0]
        
        c_i, c_m1, c_m2 = st.columns([2, 1, 1])
        c_i.markdown(f"""<div class="kpi-card"><div class="kpi-label">🏆 Meilleur Client de la sélection</div><div class="kpi-value">ID: {int(best['CustomerID'])}</div></div>""", unsafe_allow_html=True)
        c_m1.metric("Commandes", int(best['InvoiceNo']))
        c_m2.metric("Valeur Nette", f"{best['ScoreNet']:,.0f} €")
        
        st.write("##")
        l, r = st.columns(2)
        l.markdown("**📊 Top 10 Clients (Nombre de Commandes)**")
        l.plotly_chart(px.bar(client_stats.nlargest(10, 'InvoiceNo'), x='InvoiceNo', y=client_stats.nlargest(10, 'InvoiceNo')['CustomerID'].astype(int).astype(str), orientation='h', template="plotly_dark", color_discrete_sequence=['#FBBF24']).update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis={'categoryorder':'total ascending'}), use_container_width=True)
        r.markdown("**💰 Top 10 Clients (Valeur Totale)**")
        r.plotly_chart(px.bar(client_stats.nlargest(10, 'TotalRevenue'), x='TotalRevenue', y=client_stats.nlargest(10, 'TotalRevenue')['CustomerID'].astype(int).astype(str), orientation='h', template="plotly_dark", color_discrete_sequence=['#10B981']).update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis={'categoryorder':'total ascending'}), use_container_width=True)