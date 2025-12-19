import streamlit as st
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config

# ==========================================
# 1. CONFIGURARE & STIL (UI SETUP)
# ==========================================
st.set_page_config(layout="wide", page_title="Ecosistem DSU", page_icon="assets/button.svg", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .block-container { padding-top: 2rem !important; }
    h1, h2, h3, h4 { color: #F0F2F6 !important; font-family: "Helvetica Neue", Arial, sans-serif; }
    .info-card { background-color: #21262D; padding: 15px; border-radius: 4px; border-left: 4px solid #58A6FF; margin-bottom: 10px; color: #C9D1D9; }
    .description-box { background-color: #161b22; padding: 12px; border-radius: 4px; border: 1px solid #30363d; color: #8b949e; font-style: italic; font-size: 0.9rem; margin: 10px 0; }
    .metric-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px; padding: 8px; text-align: center; color: #C9D1D9; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. LOGICĂ DE DATE (BACKEND LOGIC)
# ==========================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data.csv", skipinitialspace=True).replace(r'\n', ' ', regex=True)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Partner", "Domain_Raw", "Ukraine", "Strategic", "Description"])
    
    # Normalizări
    df.columns = [c.strip() for c in df.columns]
    for col in ["Ukraine", "Strategic"]:
        if col not in df.columns: df[col] = False
        df[col] = df[col].apply(lambda x: str(x).strip().lower() in ["da", "true", "x", "1", "yes"])
    
    if "Description" not in df.columns: df["Description"] = "Fără descriere."
    df["Description"] = df["Description"].fillna("-")
    return df

def process_graph_data(df):
    """Transformă DataFrame-ul în structuri de graf (Noduri și Muchii)."""
    nodes, edges = {}, []
    
    for idx, row in df.iterrows():
        p_id, p_name = f"p_{idx}", str(row["Partner"])
        # Nod Partener
        nodes[p_id] = {
            "label": p_name, "type": "Partner", "ukraine": row["Ukraine"],
            "strategic": row["Strategic"], "desc": row["Description"]
        }
        
        # Procesare Domenii
        raw_domains = str(row["Domain_Raw"]).replace("\n", "/").replace("|", "/").split("/")
        for d in [map_domain_category(x.strip()) for x in raw_domains if x.strip()]:
            d_id = f"d_{d}"
            if d_id not in nodes:
                nodes[d_id] = {"label": d, "type": "Domain"}
            edges.append((p_id, d_id))
            
    return nodes, edges

def map_domain_category(t):
    t = t.lower()
    mapping = {
        "chimice": "Dezastre chimice", "it": "IT & C", "smart": "IT & C",
        "salvare": "Căutare-salvare", "restabilirea": "Restabilirea stării de normalitate",
        "sociale": "Servicii sociale", "logistic": "Sprijin logistic", "răspuns": "Răspuns",
        "traum": "Răspuns", "prevenire": "Prevenire", "pregătire": "Pregătire",
        "studenți": "Pregătire", "cercetare": "Cercetare", "intervenție": "Intervenție"
    }
    for k, v in mapping.items():
        if k in t: return v
    return t.title()

# ==========================================
# 3. STATE MANAGEMENT
# ==========================================
if "main_df" not in st.session_state:
    st.session_state["main_df"] = load_data()

# Master Selection: Controlează cine e focusat (din Search sau Click pe graf)
if "master_selection" not in st.session_state:
    st.session_state["master_selection"] = "- Toate -"

# Recalculăm graful complet la fiecare rulare pe baza datelor (care pot fi editate)
nodes_dict, edges_list = process_graph_data(st.session_state["main_df"])
all_partners = sorted([n["label"] for n in nodes_dict.values() if n["type"] == "Partner"])
all_domains = sorted([n["label"] for n in nodes_dict.values() if n["type"] == "Domain"])

if "filter_domains" not in st.session_state:
    st.session_state["filter_domains"] = all_domains

# ==========================================
# 4. LOGICA DE FILTRARE (VISIBILITY ENGINE)
# ==========================================
# Aceasta este "inima" logicii: decidem ce noduri sunt vizibile
visible_ids = set()
focus_node_id = None
is_focused = st.session_state["master_selection"] != "- Toate -"

# Găsim ID-ul nodului focusat (dacă există)
if is_focused:
    focus_node_id = next((nid for nid, n in nodes_dict.items() if n["label"] == st.session_state["master_selection"]), None)

if is_focused and focus_node_id:
    # MOD FOCUS: Partenerul + Vecinii săi
    visible_ids.add(focus_node_id)
    for s, t in edges_list:
        if s == focus_node_id: visible_ids.add(t)
        elif t == focus_node_id: visible_ids.add(s)
else:
    # MOD GENERAL: Filtrare după Domenii
    domain_ids = {nid for nid, n in nodes_dict.items() if n["type"] == "Domain" and n["label"] in st.session_state["filter_domains"]}
    visible_ids.update(domain_ids)
    # Adăugăm partenerii conectați la domeniile vizibile
    visible_ids.update({s for s, t in edges_list if t in domain_ids})

# ==========================================
# 5. LAYOUT UI
# ==========================================
col_ctrl, col_graph = st.columns([1, 4])

# --- LEFT PANEL: CONTROL & INFO ---
with col_ctrl:
    st.markdown("### Panou de control")
    
    # 1. Search Bar (Bidirectional Sync)
    def update_selection():
        st.session_state["master_selection"] = st.session_state["dropdown_box"]
    
    curr_idx = all_partners.index(st.session_state["master_selection"]) + 1 if is_focused else 0
    st.selectbox("Caută Organizație:", ["- Toate -"] + all_partners, index=curr_idx, key="dropdown_box", on_change=update_selection)

    st.divider()

    # 2. Stats & Filters
    if not is_focused:
        st.markdown(f"**Statistici:** {len(all_partners)} Parteneri | {len(all_domains)} Domenii")
        with st.expander("Filtrare Domenii", expanded=True):
            if st.button("Select All"): st.session_state["filter_domains"] = all_domains; st.rerun()
            if st.button("Deselect All"): st.session_state["filter_domains"] = []; st.rerun()
            st.multiselect("Domenii:", all_domains, key="filter_domains", label_visibility="collapsed")
    else:
        if st.button("⬅️ Vezi tot ecosistemul"):
            st.session_state["master_selection"] = "- Toate -"
            st.rerun()

    st.divider()

    # 3. Dynamic Details Panel
    # Afișăm detaliile pentru nodul focusat
    target_id = focus_node_id if focus_node_id else None
    
    if target_id:
        info = nodes_dict[target_id]
        st.markdown(f'<div class="info-card"><b>{info["label"]}</b></div>', unsafe_allow_html=True)
        if info["type"] == "Partner":
            st.markdown(f'<div class="description-box">{info["desc"]}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.markdown(f'<div class="metric-box">Ucraina<br>{"DA" if info["ukraine"] else "Nu"}</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box">Strategic<br>{"DA" if info["strategic"] else "Nu"}</div>', unsafe_allow_html=True)
            
            st.write("**Domenii:**")
            for d in sorted({nodes_dict[t]["label"] for s, t in edges_list if s == target_id}):
                st.markdown(f"- {d}")
    elif not is_focused:
        st.info("Selectează un nod din grafic sau caută în listă.")

# --- RIGHT PANEL: GRAPH ---
with col_graph:
    # Construim obiectele vizuale DOAR pentru nodurile vizibile
    viz_nodes, viz_edges = [], []
    
    # Calculăm gradul (conectivitatea) pentru mărime
    degrees = {n: 0 for n in nodes_dict}
    for s, t in edges_list:
        degrees[s] += 1; degrees[t] += 1

    for nid in visible_ids:
        n = nodes_dict[nid]
        if n["type"] == "Partner":
            size = 40 if nid == focus_node_id else (14 + degrees[nid] * 0.5)
            color = "#ffd700" if n["strategic"] else "#00f2c3"
            viz_nodes.append(Node(id=nid, label=n["label"][:20]+".." if len(n["label"])>20 and nid != focus_node_id else n["label"], 
                                  size=size, shape="dot", color=color, title=n["label"], font={"color": "white"}))
        else:
            viz_nodes.append(Node(id=nid, label=n["label"], size=20 + degrees[nid], shape="diamond", color="#fd79a8", font={"color": "#ffeef6"}))

    for s, t in edges_list:
        if s in visible_ids and t in visible_ids:
            viz_edges.append(Edge(source=s, target=t, color="#2d3436"))

    # Configurare Grafic
    config = Config(width=1400, height=750, directed=False, physics=True, nodeHighlightBehavior=True, highlightColor="#F7A072",
                    physics_settings={"forceAtlas2Based": {"springLength": 100, "springConstant": 0.08}})

    clicked = agraph(nodes=viz_nodes, edges=viz_edges, config=config)

    # Logică Click -> Select
    if clicked and clicked in nodes_dict and nodes_dict[clicked]["type"] == "Partner":
        clicked_label = nodes_dict[clicked]["label"]
        if clicked_label != st.session_state["master_selection"]:
            st.session_state["master_selection"] = clicked_label
            st.rerun()

# ==========================================
# 6. EDITOR DE DATE (FOOTER)
# ==========================================
st.divider()
with st.expander("Editor Date (Live Update)"):
    edited = st.data_editor(st.session_state["main_df"], num_rows="dynamic", use_container_width=True, key="editor")
    if not edited.equals(st.session_state["main_df"]):
        st.session_state["main_df"] = edited
        st.rerun()
