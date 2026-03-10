import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="E-commerce Pro Analytics", layout="wide")

# --- 2. STYLE CSS ---
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
</style>
""", unsafe_allow_html=True)

# --- 3. CHARGEMENT (Pickle) ---
@st.cache_data
def load_data():
    return pd.read_pickle('cleaned_ecommerce_data.pkl')

try:
    df_raw = load_data()
except:
    st.error("Fichier 'cleaned_ecommerce_data.pkl' introuvable. Lancez votre notebook d'abord.")
    st.stop()

# --- 4. SIDEBAR ---
st.sidebar.header("📍 Filtres")
sel_continents = st.sidebar.multiselect("Continents", options=sorted(df_raw['Continent'].unique()), default=df_raw['Continent'].unique())
avail_countries = sorted(df_raw[df_raw['Continent'].isin(sel_continents)]['Country'].unique())
sel_countries = st.sidebar.multiselect("Pays", options=avail_countries, default=avail_countries)

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

sc, sp = stats(df), stats(df_c)
def delta(curr, prev): return ((curr - prev) / prev * 100) if prev > 0 else 0

# --- 7. INTERFACE PAR ONGLETS ---
st.title("🌍 Business Intelligence Dashboard")
tab_global, tab_client = st.tabs(["📊 Vue Globale", "👥 Vue Client"])

# ==========================================
# ONGLET 1 : VUE GLOBALE
# ==========================================
with tab_global:
    # ROW 1: KPIs
    cols = st.columns(5)
    names = ["Revenue", "Commandes", "Clients", "Panier Moyen", "Pertes (Annul.)"]
    for i, col in enumerate(cols):
        val, d = sc[i], delta(sc[i], sp[i])
        color = "up" if (d >= 0 if i != 4 else d <= 0) else "down"
        col.markdown(f"""<div class="kpi-card"><div class="kpi-label">{names[i]}</div><div class="kpi-value">{val:,.0f}{' €' if i in [0,3,4] else ''}</div>
        <div class="{color}">{"↑" if d>=0 else "↓"} {abs(d):.1f}% <span style="color:#64748B">{comp_label}</span></div></div>""", unsafe_allow_html=True)

    # ROW 2: Graphiques
    c_left, c_right = st.columns([2, 1])
    with c_left:
        st.subheader("📈 Dynamique du Chiffre d'Affaires Net")
        if not df.empty:
            net_data = df.groupby(g_col)['TotalRevenue'].sum().reset_index()
            if g_col == 'Month': net_data['Month'] = net_data['Month'].astype(str)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=net_data[g_col], y=net_data['TotalRevenue'].clip(lower=0), mode='lines', fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.3)', line=dict(color='#10B981'), name='Profit'))
            fig.add_trace(go.Scatter(x=net_data[g_col], y=net_data['TotalRevenue'].clip(upper=0), mode='lines', fill='tozeroy', fillcolor='rgba(244, 63, 94, 0.3)', line=dict(color='#F43F5E'), name='Perte'))
            fig.update_layout(template="plotly_dark", hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with c_right:
        st.subheader("📊 Part des Pays")
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
    if df.empty:
        st.warning("Aucune donnée disponible pour les filtres sélectionnés.")
    else:
        st.subheader("💎 Analyse des meilleurs clients")
        
        # --- CALCULS CLIENTS ---
        client_stats = df.groupby('CustomerID').agg({
            'InvoiceNo': 'nunique',
            'TotalRevenue': 'sum'
        }).reset_index()
        
        # Calcul spécifique demandé : Valeur nette - nombre de retours
        # Note : On compte le nombre de transactions négatives pour ce client
        returns_count = df[df['TotalRevenue'] < 0].groupby('CustomerID')['InvoiceNo'].nunique().reset_index()
        returns_count.columns = ['CustomerID', 'NbRetours']
        
        client_stats = pd.merge(client_stats, returns_count, on='CustomerID', how='left').fillna(0)
        client_stats['ScoreNet'] = client_stats['TotalRevenue'] - client_stats['NbRetours']
        
        best_client_row = client_stats.nlargest(1, 'InvoiceNo').iloc[0]
        
        # --- AFFICHAGE MEILLEUR CLIENT ---
        c_info, c_metric1, c_metric2 = st.columns([2, 1, 1])
        
        with c_info:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">🏆 Meilleur Client de la sélection</div>
                <div class="kpi-value">ID: {int(best_client_row['CustomerID'])}</div>
                <div style="color:#94A3B8; font-size:0.9rem; margin-top:5px;">
                    Basé sur le nombre de commandes uniques
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_metric1:
            st.metric("Total Commandes", f"{int(best_client_row['InvoiceNo'])}")
            
        with c_metric2:
            st.metric("Valeur Nette (vs Retours)", f"{best_client_row['ScoreNet']:,.2f} €")
        
        st.write("##")
        
        # --- GRAPHQUES PROPORTION ---
        col_bar1, col_bar2 = st.columns(2)
        
        with col_bar1:
            st.markdown("**📊 Top 10 Clients (Nombre de Commandes)**")
            top_10_qty = client_stats.nlargest(10, 'InvoiceNo')
            top_10_qty['CustomerID'] = top_10_qty['CustomerID'].astype(int).astype(str)
            fig_qty = px.bar(top_10_qty, x='InvoiceNo', y='CustomerID', orientation='h', 
                             color_discrete_sequence=['#FBBF24'], template="plotly_dark")
            fig_qty.update_layout(yaxis={'categoryorder':'total ascending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_qty, use_container_width=True)
            
        with col_bar2:
            st.markdown("**💰 Top 10 Clients (Valeur Nette Totale)**")
            top_10_val = client_stats.nlargest(10, 'TotalRevenue')
            top_10_val['CustomerID'] = top_10_val['CustomerID'].astype(int).astype(str)
            fig_val = px.bar(top_10_val, x='TotalRevenue', y='CustomerID', orientation='h', 
                             color_discrete_sequence=['#10B981'], template="plotly_dark")
            fig_val.update_layout(yaxis={'categoryorder':'total ascending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_val, use_container_width=True)
            
        st.divider()
        st.markdown("**📄 Détail des 50 plus gros clients**")
        st.dataframe(client_stats.nlargest(50, 'TotalRevenue').drop(columns=['ScoreNet']), use_container_width=True)