import streamlit as st
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config

# ---------------------------------
# 0. CONFIGURARE PAGINĂ
# ---------------------------------

st.set_page_config(
    layout="wide",
    page_title="Ecosistem DSU", 
    page_icon="assets/button.svg",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0E1117;
    }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }
    h1, h2, h3, h4, h5 {
        color: #F0F2F6 !important;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    }
    .info-card {
        background-color: #21262D;
        padding: 15px;
        border-radius: 4px;
        border-left: 4px solid #58A6FF;
        margin-bottom: 10px;
        color: #C9D1D9;
        font-size: 0.9rem;
    }
    .description-box {
        background-color: #161b22;
        padding: 12px;
        border-radius: 4px;
        border: 1px solid #30363d;
        color: #8b949e;
        font-style: italic;
        font-size: 0.9rem;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .metric-box {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 4px;
        padding: 8px;
        text-align: center;
        margin: 5px 0;
        color: #C9D1D9;
        font-size: 0.85rem;
    }
    .stButton button {
        width: 100%;
        border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------
# 1. FUNCȚII UTILITARE
# ---------------------------------

def clean_domains(domain_str: str) -> list[str]:
    if pd.isna(domain_str): return []
    text = str(domain_str).strip().replace("\n", "/").replace("|", "/").replace("\\", "/")
    return [p.strip() for p in text.split("/") if p.strip()]

def map_domain_category(raw_piece: str) -> str:
    t = raw_piece.lower()
    if "dezastre chimice" in t: return "Dezastre chimice"
    if "smart city" in t or "it & c" in t or "it " in t: return "IT & C"
    if "căutare" in t or "caini de salvare" in t or "câini de salvare" in t: return "Căutare-salvare"
    if "restabilirea stării de normalitate" in t: return "Restabilirea stării de normalitate"
    if "servicii sociale" in t: return "Servicii sociale"
    if "sprijin tehnic logistic" in t: return "Sprijin logistic"
    if "răspuns" in t or "traum" in t or "psiholog" in t: return "Răspuns"
    if "prevenire" in t: return "Prevenire"
    if "pregătire" in t or "practică studenți" in t or "training" in t: return "Pregătire"
    if "cercetare" in t: return "Cercetare"
    if "intervenție" in t: return "Intervenție"
    return raw_piece.strip()

# ---------------------------------
# 2. ÎNCĂRCARE DATE
# ---------------------------------

@st.cache_data
def load_initial_data():
    try:
        df = pd.read_csv("data.csv", skipinitialspace=True)
        df = df.replace(r'\n', ' ', regex=True)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Partner", "Domain_Raw", "Ukraine", "Strategic", "Description"]), True

    df.columns = [c.strip() for c in df.columns]
    
    if "Ukraine" not in df.columns: df["Ukraine"] = False
    if "Strategic" not in df.columns: df["Strategic"] = False
    if "Description" not in df.columns: df["Description"] = "Fără descriere."
    
    df["Description"] = df["Description"].fillna("Descriere indisponibilă.")

    def normalize_bool(val):
        return str(val).strip().lower() in ["da", "true", "x", "1", "yes"]

    df["Ukraine"] = df["Ukraine"].apply(normalize_bool)
    df["Strategic"] = df["Strategic"].apply(normalize_bool)
    
    return df, False

if "main_df" not in st.session_state:
    loaded_df, err = load_initial_data()
    st.session_state["main_df"] = loaded_df

# ---------------------------------
# 3. PREGĂTIRE DATE (NODURI & MUCHII)
# ---------------------------------

current_df = st.session_state["main_df"].copy()
current_df["Domains_List"] = current_df["Domain_Raw"].apply(clean_domains)

nodes_dict = {}
edges_list = []

for idx, row in current_df.iterrows():
    p_id = f"p_{idx}"
    p_name = str(row["Partner"])

    nodes_dict[p_id] = {
        "label": p_name,
        "type": "Partner",
        "ukraine": row["Ukraine"],
        "strategic": row["Strategic"],
        "raw_domain": str(row["Domain_Raw"]),
        "description": str(row["Description"])
    }

    for raw_dom in row["Domains_List"]:
        dom_cat = map_domain_category(raw_dom)
        d_id = f"d_{dom_cat}"

        if d_id not in nodes_dict:
            nodes_dict[d_id] = { "label": dom_cat, "type": "Domain" }
        edges_list.append((p_id, d_id))

all_domain_labels = sorted(list(set(info["label"] for info in nodes_dict.values() if info["type"] == "Domain")))
all_partners_labels = sorted(list(set(info["label"] for info in nodes_dict.values() if info["type"] == "Partner")))

# ---------------------------------
# 4. GESTIONARE STATE (MASTER SELECTION)
# ---------------------------------

# Variabila "master_selection" ține minte cine e selectat (indiferent de sursă: dropdown sau click)
if "master_selection" not in st.session_state:
    st.session_state["master_selection"] = "- Toate -"

if "filter_domains" not in st.session_state:
    st.session_state["filter_domains"] = all_domain_labels

# ---------------------------------
# 5. LAYOUT & INTERFAȚĂ
# ---------------------------------

col_controls, col_graph = st.columns([1, 4])

with col_controls:
    st.markdown("### Panou de control")

    # --- SEARCH BAR SINCRONIZAT ---
    st.markdown("#### Caută Organizație")
    
    search_options = ["- Toate -"] + all_partners_labels
    
    # Calculăm indexul pentru a forța dropdown-ul să arate selecția curentă (Master)
    try:
        current_index = search_options.index(st.session_state["master_selection"])
    except ValueError:
        current_index = 0
        st.session_state["master_selection"] = "- Toate -"

    # Callback pentru când userul schimbă manual dropdown-ul
    def on_dropdown_change():
        st.session_state["master_selection"] = st.session_state["dropdown_key"]

    selected_partner_search = st.selectbox(
        "Alege un partener:", 
        options=search_options,
        index=current_index,
        key="dropdown_key",
        on_change=on_dropdown_change
    )
    
    is_search_active = st.session_state["master_selection"] != "- Toate -"

    st.markdown("---")

    # STATISTICI
    total_partners = sum(1 for n in nodes_dict.values() if n["type"] == "Partner")
    total_domains = sum(1 for n in nodes_dict.values() if n["type"] == "Domain")
    st.markdown(
        f"""<div style="font-size: 0.85rem; color: #8b949e; margin-bottom: 20px;">
        Parteneri: <b>{total_partners}</b> | Domenii: <b>{total_domains}</b>
        </div>""", unsafe_allow_html=True
    )

    # FILTRE
    if not is_search_active:
        st.markdown("#### Filtrare domenii")
        c_btn1, c_btn2 = st.columns(2)
        if c_btn1.button("Selectează tot"):
            st.session_state["filter_domains"] = all_domain_labels
            st.rerun()
        if c_btn2.button("Deselectează tot"):
            st.session_state["filter_domains"] = []
            st.rerun()

        selected_domains = st.multiselect("Domenii vizibile:", options=all_domain_labels, key="filter_domains")
    else:
        st.info(f"Mod Focus: **{st.session_state['master_selection']}**")
        if st.button("⬅️ Vezi toate organizațiile"):
            st.session_state["master_selection"] = "- Toate -"
            st.rerun()
        selected_domains = all_domain_labels 

    st.markdown("---")

    # --- DETALII NOD ---
    focus_node_id = None
    if is_search_active:
        for nid, info in nodes_dict.items():
            if info["label"] == st.session_state["master_selection"] and info["type"] == "Partner":
                focus_node_id = nid
                break
    
    if focus_node_id:
        info = nodes_dict[focus_node_id]
        st.markdown(f'<div class="info-card"><b>Partener DSU</b><br>{info["label"]}</div>', unsafe_allow_html=True)
        if info.get("description") and info["description"] != "nan":
            st.markdown(f'<div class="description-box">{info["description"]}</div>', unsafe_allow_html=True)

        ukr_text = "DA" if info["ukraine"] else "Nu"
        strat_text = "DA" if info["strategic"] else "Nu"
        c1, c2 = st.columns(2)
        c1.markdown(f'<div class="metric-box">Ucraina<br><b>{ukr_text}</b></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-box">Strategic<br><b>{strat_text}</b></div>', unsafe_allow_html=True)

        st.markdown("<b>Domenii asociate:</b>", unsafe_allow_html=True)
        domains = [nodes_dict[t]["label"] for s, t in edges_list if s == focus_node_id]
        for d in sorted(set(domains)):
            st.markdown(f"- {d}")

    elif not is_search_active:
        st.info("Selectează un partener din grafic sau din meniu.")


# --- COLOANA DREAPTA: GRAF ---
with col_graph:
    st.markdown("### Ecosistem DSU")
    
    nodes_viz = []
    edges_viz = []
    COLOR_PARTNER = "#00f2c3"
    COLOR_STRATEGIC = "#ffd700"
    COLOR_DOMAIN = "#fd79a8"

    degree: dict[str, int] = {}
    for s, t in edges_list:
        degree[s] = degree.get(s, 0) + 1
        degree[t] = degree.get(t, 0) + 1

    # --- LOGICA DE VIZIBILITATE ---
    visible_node_ids = set()
    
    if is_search_active and focus_node_id:
        visible_node_ids.add(focus_node_id)
        for s, t in edges_list:
            if s == focus_node_id: visible_node_ids.add(t)
            elif t == focus_node_id: visible_node_ids.add(s)
    else:
        for nid, info in nodes_dict.items():
            if info["type"] == "Domain" and info["label"] in selected_domains:
                visible_node_ids.add(nid)
        temp_partners = set()
        for s, t in edges_list:
            if t in visible_node_ids: temp_partners.add(s)
        visible_node_ids.update(temp_partners)

    for nid in visible_node_ids:
        info = nodes_dict[nid]
        if info["type"] == "Partner":
            full_label = info["label"]
            if is_search_active and nid == focus_node_id:
                display_label = full_label
                size = 40
                font_size = 18
            else:
                display_label = full_label if len(full_label) <= 20 else full_label[:20] + "..."
                size = 14 + degree.get(nid, 1) * 0.4
                font_size = 14
            
            color = COLOR_STRATEGIC if info.get("strategic") else COLOR_PARTNER
            nodes_viz.append(Node(id=nid, label=display_label, title=full_label, size=size, shape="dot", color=color, font={"color": "white", "size": font_size}))
        else: 
            nodes_viz.append(Node(id=nid, label=info["label"], title=info["label"], size=20 + degree.get(nid, 1) * 0.5, shape="diamond", color=COLOR_DOMAIN, font={"color": "#ffeef6", "size": 14}))

    for s, t in edges_list:
        if s in visible_node_ids and t in visible_node_ids:
            edges_viz.append(Edge(source=s, target=t, color="#2d3436", width=1.0))

    config = Config(
        width=1200, height=750, directed=False, physics=True, hierarchical=False,
        nodeHighlightBehavior=True, highlightColor="#F7A072", collapsible=True,
        physics_settings={"forceAtlas2Based": {"gravitationalConstant": -50, "centralGravity": 0.005, "springLength": 200, "springConstant": 0.05}, "minVelocity": 0.75, "solver": "forceAtlas2Based"},
    )

    clicked_id = agraph(nodes=nodes_viz, edges=edges_viz, config=config)
    
    # --- LOGICA DE SINCRONIZARE CLICK -> MASTER STATE ---
    if clicked_id:
        if clicked_id in nodes_dict and nodes_dict[clicked_id]["type"] == "Partner":
            clicked_name = nodes_dict[clicked_id]["label"]
            # Dacă userul a dat click pe un partener diferit de ce e selectat acum
            if clicked_name != st.session_state["master_selection"]:
                st.session_state["master_selection"] = clicked_name
                st.rerun()

# --- EDITOR DATE ---
st.divider()
with st.expander("Editor Date (Live Update)", expanded=False):
    st.write("Modifică datele și descrierile.")
    editable_df = st.data_editor(
        st.session_state["main_df"],
        num_rows="dynamic",
        use_container_width=True,
        key="data_editor_component",
        column_config={
            "Partner": st.column_config.TextColumn("Partener", width="medium"),
            "Description": st.column_config.TextColumn("Descriere", width="large"),
            "Domain_Raw": st.column_config.TextColumn("Domenii", width="medium"),
            "Strategic": st.column_config.CheckboxColumn("Strategic?", width="small"),
            "Ukraine": st.column_config.CheckboxColumn("Ucraina?", width="small")
        }
    )
    if not editable_df.equals(st.session_state["main_df"]):
        st.session_state["main_df"] = editable_df
        st.rerun()
    
    def convert_df(d):
        export = d.copy()
        export["Strategic"] = export["Strategic"].apply(lambda x: "da" if x else "")
        export["Ukraine"] = export["Ukraine"].apply(lambda x: "da" if x else "")
        return export.to_csv(index=False).encode('utf-8')

    st.download_button(label="Descarcă CSV actualizat", data=convert_df(editable_df), file_name='data_updated.csv', mime='text/csv')
