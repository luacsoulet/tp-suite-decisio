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

# --- 3. MAPPING GÉOGRAPHIQUE COMPLET ---
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

# --- 4. CHARGEMENT ---
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv', encoding='ISO-8859-1')
    df.dropna(subset=['CustomerID'], inplace=True)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['TotalRevenue'] = df['Quantity'] * df['UnitPrice']
    df['Month'] = df['InvoiceDate'].dt.to_period('M')
    df['Year'] = df['InvoiceDate'].dt.year
    df['Date'] = df['InvoiceDate'].dt.date
    df['Continent'] = df['Country'].map(COUNTRY_TO_CONTINENT).fillna('Europe')
    return df

df_raw = load_data()

# --- 5. SIDEBAR ---
st.sidebar.header("📍 Géographie")
all_continents = sorted(df_raw['Continent'].unique().tolist())
sel_continents = st.sidebar.multiselect("Continents", options=all_continents, default=all_continents)

avail_countries = sorted(df_raw[df_raw['Continent'].isin(sel_continents)]['Country'].unique().tolist())
sel_countries = st.sidebar.multiselect("Pays", options=avail_countries, default=avail_countries)

st.sidebar.divider()
st.sidebar.header("📅 Temporalité")
time_option = st.sidebar.selectbox("Période", ["Mois actuel", "Année en cours", "Toute la durée"])

# --- 6. LOGIQUE TEMPORELLE ---
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

# --- 7. CALCULS KPIs ---
def stats(d):
    if d.empty: return 0, 0, 0, 0, 0
    # Chiffre d'affaires Brut (uniquement positif)
    r = d[d['TotalRevenue'] > 0]['TotalRevenue'].sum()
    o = d['InvoiceNo'].nunique()
    c = d['CustomerID'].nunique()
    # Pertes brutes (uniquement négatif)
    l = abs(d[d['TotalRevenue'] < 0]['TotalRevenue'].sum())
    return r, o, c, (r/o if o>0 else 0), l

sc, sp = stats(df), stats(df_c)
def delta(curr, prev): return ((curr - prev) / prev * 100) if prev > 0 else 0

# --- 8. AFFICHAGE ---
st.title("🌍 Business Intelligence Dashboard")

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
        # 1. Calculer le revenu NET (Ventes + Annulations) par période
        net_data = df.groupby(g_col)['TotalRevenue'].sum().reset_index()
        if g_col == 'Month': net_data['Month'] = net_data['Month'].astype(str)
        
        # 2. Séparer en deux séries pour la couleur (Profit vs Perte)
        net_data['Profit'] = net_data['TotalRevenue'].apply(lambda x: x if x > 0 else 0)
        net_data['Loss'] = net_data['TotalRevenue'].apply(lambda x: x if x < 0 else 0)

        fig = go.Figure()

        # Partie Verte (Profit Net)
        fig.add_trace(go.Scatter(
            x=net_data[g_col], y=net_data['Profit'],
            mode='lines', line=dict(width=2, color='#10B981'),
            fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.3)',
            name='Profit Net',
            hovertemplate='Profit: %{y:,.2f} €<extra></extra>'
        ))

        # Partie Rouge (Perte Nette)
        fig.add_trace(go.Scatter(
            x=net_data[g_col], y=net_data['Loss'],
            mode='lines', line=dict(width=2, color='#F43F5E'),
            fill='tozeroy', fillcolor='rgba(244, 63, 94, 0.3)',
            name='Perte Nette',
            hovertemplate='Perte: %{y:,.2f} €<extra></extra>'
        ))

        fig.update_layout(
            template="plotly_dark",
            hovermode="x unified",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#334155', zeroline=True, zerolinecolor='#F8FAFC')
        )
        st.plotly_chart(fig, use_container_width=True)

with c_right:
    st.subheader("📊 Part des Pays")
    if not df.empty:
        geo = df.groupby('Country')['InvoiceNo'].nunique().reset_index().sort_values('InvoiceNo', ascending=False)
        nb_c = len(sel_continents)
        plot_df = geo if (nb_c == 1 and len(geo) <= 7) else pd.concat([geo.head(5), pd.DataFrame({'Country': ['Autres'], 'InvoiceNo': [geo.iloc[5:]['InvoiceNo'].sum()]})])
        
        fig_p = px.pie(plot_df, values='InvoiceNo', names='Country', hole=0.5, template="plotly_dark")
        fig_p.update_traces(textinfo='percent+label')
        fig_p.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig_p, use_container_width=True)

# ROW 3: Produits
r3l, r3r = st.columns(2)
with r3l:
    st.subheader("🏆 Top 10 Vendus")
    top_v = df[df['Quantity'] > 0].groupby('Description')['Quantity'].sum().nlargest(10).reset_index()
    st.plotly_chart(px.bar(top_v, x='Quantity', y='Description', orientation='h', template="plotly_dark", color_discrete_sequence=['#818CF8']).update_layout(yaxis={'categoryorder':'total ascending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
with r3r:
    st.subheader("🚫 Top 10 Annulés")
    top_r = df[df['Quantity'] < 0].groupby('Description')['Quantity'].sum().abs().nlargest(10).reset_index()
    st.plotly_chart(px.bar(top_r, x='Quantity', y='Description', orientation='h', template="plotly_dark", color_discrete_sequence=['#F43F5E']).update_layout(yaxis={'categoryorder':'total ascending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'), use_container_width=True)