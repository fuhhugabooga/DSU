import streamlit as st
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config

# ---------------------------------
# 0. CONFIGURARE PAGINĂ & BRANDING
# ---------------------------------

st.set_page_config(
    layout="wide",
    page_title="Oswald Software", 
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
    """Împarte Domain_Raw în bucăți."""
    if pd.isna(domain_str):
        return []
    text = str(domain_str).strip()
    if text == "" or text == "-":
        return []

    text = (
        text.replace("\n", "/")
        .replace("|", "/")
        .replace("\\", "/")
    )

    parts = [p.strip() for p in text.split("/") if p.strip()]
    return parts

def map_domain_category(raw_piece: str) -> str:
    """Transformă bucata din Domain_Raw într-o categorie simplă."""
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
# 2. ÎNCĂRCARE DATE INIȚIALĂ
# ---------------------------------

@st.cache_data
def load_initial_data():
    """Citește data.csv de pe disk doar la prima rulare."""
    try:
        df = pd.read_csv("data.csv", skipinitialspace=True)
        # Curățare generală caractere
        df = df.replace(r'\n', ' ', regex=True)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Partner", "Domain_Raw", "Ukraine", "Strategic", "Description"]), True

    df.columns = [c.strip() for c in df.columns]
    
    # Asigurăm existența coloanelor
    if "Ukraine" not in df.columns: df["Ukraine"] = False
    if "Strategic" not in df.columns: df["Strategic"] = False
    if "Description" not in df.columns: df["Description"] = "Fără descriere." # Default value
    
    # Umplem valorile lipsă la descriere
    df["Description"] = df["Description"].fillna("Descriere indisponibilă.")

    def normalize_bool(val):
        return str(val).strip().lower() in ["da", "true", "x", "1", "yes"]

    df["Ukraine"] = df["Ukraine"].apply(normalize_bool)
    df["Strategic"] = df["Strategic"].apply(normalize_bool)
    
    return df, False

# Inițializare Session State pentru Dataframe
if "main_df" not in st.session_state:
    loaded_df, err = load_initial_data()
    st.session_state["main_df"] = loaded_df
    if err:
        st.error("Fișierul 'data.csv' nu a fost găsit.")

# ---------------------------------
# 3. LAYOUT & LOGICĂ
# ---------------------------------

col_controls, col_graph = st.columns([1, 4])

# Pregătire date curente
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
        "description": str(row["Description"]) # [NOU] Salvăm descrierea în nod
    }

    for raw_dom in row["Domains_List"]:
        dom_cat = map_domain_category(raw_dom)
        d_id = f"d_{dom_cat}"

        if d_id not in nodes_dict:
            nodes_dict[d_id] = {
                "label": dom_cat,
                "type": "Domain",
            }
        edges_list.append((p_id, d_id))

# State Selecție
if "selected_id" not in st.session_state:
    st.session_state["selected_id"] = None

# Liste pentru filtre/search
all_domain_labels = sorted(list(set(
    info["label"] for info in nodes_dict.values() if info["type"] == "Domain"
)))
all_partners_labels = sorted(list(set(
    info["label"] for info in nodes_dict.values() if info["type"] == "Partner"
)))

if "filter_domains" not in st.session_state:
    st.session_state["filter_domains"] = all_domain_labels

# --- COLOANA STÂNGA: CONTROALE ---
with col_controls:
    st.markdown("### Panou de control")

    # SEARCH BAR
    st.markdown("#### Caută Organizație")
    search_options = ["- Toate -"] + all_partners_labels
    selected_partner_search = st.selectbox("Alege un partener:", options=search_options)
    is_search_active = selected_partner_search != "- Toate -"

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
        st.info(f"Filtru activ pe: **{selected_partner_search}**")
        selected_domains = all_domain_labels

    st.markdown("---")
    
    # Buton Reset Zoom
    if st.session_state["selected_id"]:
        if st.button("⬅️ Înapoi la vedere generală"):
            st.session_state["selected_id"] = None
            st.rerun()

    # --- DETALII NOD (CU DESCRIERE) ---
    search_node_id = None
    if is_search_active:
        for nid, info in nodes_dict.items():
            if info["label"] == selected_partner_search and info["type"] == "Partner":
                search_node_id = nid
                break
    
    current_display_id = st.session_state["selected_id"]
    if is_search_active and search_node_id:
        current_display_id = search_node_id

    if current_display_id and current_display_id in nodes_dict:
        info = nodes_dict[current_display_id]

        if info["type"] == "Partner":
            # Titlu Partener
            st.markdown(f'<div class="info-card"><b>Partener DSU</b><br>{info["label"]}</div>', unsafe_allow_html=True)
            
            # [NOU] Afișare Descriere Contextuală
            if info.get("description") and info["description"] != "nan":
                 st.markdown(f'<div class="description-box">{info["description"]}</div>', unsafe_allow_html=True)

            ukr_text = "DA" if info["ukraine"] else "Nu"
            strat_text = "DA" if info["strategic"] else "Nu"

            c1, c2 = st.columns(2)
            c1.markdown(f'<div class="metric-box">Ucraina<br><b>{ukr_text}</b></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box">Strategic<br><b>{strat_text}</b></div>', unsafe_allow_html=True)

            st.markdown("<b>Domenii asociate:</b>", unsafe_allow_html=True)
            domains = [nodes_dict[t]["label"] for s, t in edges_list if s == current_display_id]
            if domains:
                for d in sorted(set(domains)):
                    st.markdown(f"- {d}")

        else:  # Domain
            st.markdown(f'<div class="info-card"><b>Domeniu</b><br>{info["label"]}</div>', unsafe_allow_html=True)
            partners = [nodes_dict[s]["label"] for s, t in edges_list if t == current_display_id]
            st.markdown(f"Parteneri în domeniu: **{len(partners)}**")
            if partners:
                with st.expander("Vezi lista parteneri"):
                    for p in sorted(set(partners)):
                        st.markdown(f"- {p}")
    elif not is_search_active:
        st.info("Selectează un nod sau caută o organizație.")


# --- COLOANA DREAPTA: GRAF ---
with col_graph:
    st.markdown("### Ecosistem DSU")
    
    nodes_viz = []
    edges_viz = []
    COLOR_PARTNER = "#00f2c3"
    COLOR_STRATEGIC = "#ffd700"
    COLOR_DOMAIN = "#fd79a8"

    # Calcul Grad
    degree: dict[str, int] = {}
    for s, t in edges_list:
        degree[s] = degree.get(s, 0) + 1
        degree[t] = degree.get(t, 0) + 1

    # Filtrare Vizuală
    visible_node_ids = set()
    
    if is_search_active and search_node_id:
        visible_node_ids.add(search_node_id)
        for s, t in edges_list:
            if s == search_node_id: visible_node_ids.add(t)
            elif t == search_node_id: visible_node_ids.add(s)
    else:
        for nid, info in nodes_dict.items():
            if info["type"] == "Domain" and info["label"] in selected_domains:
                visible_node_ids.add(nid)
        temp_partners = set()
        for s, t in edges_list:
            if t in visible_node_ids: temp_partners.add(s)
        visible_node_ids.update(temp_partners)

    # Construire Noduri
    for nid in visible_node_ids:
        info = nodes_dict[nid]
        if info["type"] == "Partner":
            full_label = info["label"]
            if is_search_active and nid == search_node_id:
                display_label = full_label
                size = 35
            else:
                display_label = full_label if len(full_label) <= 20 else full_label[:20] + "..."
                size = 14 + degree.get(nid, 1) * 0.4

            color = COLOR_STRATEGIC if info.get("strategic") else COLOR_PARTNER
            nodes_viz.append(Node(
                id=nid, label=display_label, title=full_label, size=size,
                shape="dot", color=color, font={"color": "white", "size": 14}
            ))
        else: # Domain
            nodes_viz.append(Node(
                id=nid, label=info["label"], title=info["label"],
                size=20 + degree.get(nid, 1) * 0.5, shape="diamond",
                color=COLOR_DOMAIN, font={"color": "#ffeef6", "size": 14}
            ))

    # Construire Muchii
    for s, t in edges_list:
        if s in visible_node_ids and t in visible_node_ids:
            edges_viz.append(Edge(source=s, target=t, color="#2d3436", width=1.0))

    config = Config(
        width=1200, height=750, directed=False, physics=True, hierarchical=False,
        nodeHighlightBehavior=True, highlightColor="#F7A072", collapsible=True,
        physics_settings={
            "forceAtlas2Based": {
                "gravitationalConstant": -50, "centralGravity": 0.005,
                "springLength": 200, "springConstant": 0.05,
            },
            "minVelocity": 0.75, "solver": "forceAtlas2Based",
        },
    )

    clicked_id = agraph(nodes=nodes_viz, edges=edges_viz, config=config)
    
    if clicked_id is not None and clicked_id != st.session_state["selected_id"]:
        st.session_state["selected_id"] = clicked_id
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
            "Description": st.column_config.TextColumn("Descriere", width="large"), # [NOU]
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

    st.download_button(
        label="Descarcă CSV actualizat",
        data=convert_df(editable_df),
        file_name='data_updated.csv',
        mime='text/csv',
    )
