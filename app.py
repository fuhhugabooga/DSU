import streamlit as st
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config

# ---------------------------------
# 0. CONFIGURARE PAGINĂ & STIL
# ---------------------------------

st.set_page_config(
    layout="wide",
    page_title="Ecosistem DSU",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0E1117;
    }
    /* Reduce padding-ul de sus al paginii */
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

    # unificăm separatorii în "/"
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

    if "dezastre chimice" in t:
        return "Dezastre chimice"
    if "smart city" in t or "it & c" in t or "it " in t:
        return "IT & C"
    if "căutare" in t or "caini de salvare" in t or "câini de salvare" in t:
        return "Căutare-salvare"
    if "restabilirea stării de normalitate" in t:
        return "Restabilirea stării de normalitate"
    if "servicii sociale" in t:
        return "Servicii sociale"
    if "sprijin tehnic logistic" in t:
        return "Sprijin logistic"
    if "răspuns" in t or "traum" in t or "psiholog" in t:
        return "Răspuns"
    if "prevenire" in t:
        return "Prevenire"
    if "pregătire" in t or "practică studenți" in t or "training" in t:
        return "Pregătire"
    if "cercetare" in t:
        return "Cercetare"
    if "intervenție" in t:
        return "Intervenție"

    return raw_piece.strip()

# ---------------------------------
# 2. ÎNCĂRCARE DATE
# ---------------------------------

@st.cache_data
def load_data():
    """Citește data.csv de pe disk."""
    try:
        df = pd.read_csv("data.csv")
    except FileNotFoundError:
        st.error("Fișierul 'data.csv' nu a fost găsit. Te rog încarcă-l.")
        return {}, [], pd.DataFrame(), True

    df.columns = [c.strip() for c in df.columns]

    required_cols = ["Partner", "Domain_Raw"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Lipsesc coloanele obligatorii din CSV: {missing}")
        return {}, [], df, True

    if "Ukraine" not in df.columns:
        df["Ukraine"] = False
    
    if "Strategic" not in df.columns:
        df["Strategic"] = False
        missing_strategic = True
    else:
        missing_strategic = False

    def normalize_bool(val):
        return str(val).strip().lower() in ["da", "true", "x", "1", "yes"]

    df["Ukraine"] = df["Ukraine"].apply(normalize_bool)
    df["Strategic"] = df["Strategic"].apply(normalize_bool)
    df["Domains_List"] = df["Domain_Raw"].apply(clean_domains)

    nodes_dict: dict[str, dict] = {}
    edges_list: list[tuple[str, str]] = []

    for idx, row in df.iterrows():
        p_id = f"p_{idx}"

        nodes_dict[p_id] = {
            "label": str(row["Partner"]),
            "type": "Partner",
            "ukraine": row["Ukraine"],
            "strategic": row["Strategic"],
            "raw_domain": str(row["Domain_Raw"]),
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

    return nodes_dict, edges_list, df, missing_strategic

nodes_data, edges_data, df, missing_strategic = load_data()

# ---------------------------------
# 3. STATE PENTRU SELECȚIE & FILTRE
# ---------------------------------

if "selected_id" not in st.session_state:
    st.session_state["selected_id"] = None

# Lista completă de domenii pentru filtre
all_domain_labels = sorted(list(set(
    info["label"] for info in nodes_data.values() if info["type"] == "Domain"
)))

if "filter_domains" not in st.session_state:
    st.session_state["filter_domains"] = all_domain_labels

# ---------------------------------
# 4. LAYOUT: CONTROALE (Stânga) + HARTĂ (Dreapta)
# ---------------------------------

col_controls, col_graph = st.columns([1, 4])

# --- COLOANA STÂNGA: FILTRE & DETALII ---
with col_controls:
    st.markdown("### Panou de cntrol")

    # Statistici Generale
    total_partners = sum(1 for n in nodes_data.values() if n["type"] == "Partner")
    total_domains = sum(1 for n in nodes_data.values() if n["type"] == "Domain")
    total_ukraine = sum(1 for n in nodes_data.values() if n["type"] == "Partner" and n.get("ukraine"))
    total_strategic = sum(1 for n in nodes_data.values() if n["type"] == "Partner" and n.get("strategic"))

    st.markdown(
        f"""
        <div style="font-size: 0.85rem; color: #8b949e; margin-bottom: 20px;">
        Parteneri total: <b>{total_partners}</b><br>
        Domenii total: <b>{total_domains}</b><br>
        Parteneri Ucraina: <b>{total_ukraine}</b><br>
        Parteneri Strategici: <b>{total_strategic}</b>
        </div>
        """, unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("#### Filtrare domenii")
    
    # Butoane Select/Deselect
    c_btn1, c_btn2 = st.columns(2)
    if c_btn1.button("Selectează tot"):
        st.session_state["filter_domains"] = all_domain_labels
        st.rerun()
    if c_btn2.button("Deselectează tot"):
        st.session_state["filter_domains"] = []
        st.rerun()

    selected_domains = st.multiselect(
        "Alege domeniile vizibile:",
        options=all_domain_labels,
        key="filter_domains"
    )

    st.markdown("---")

    # Buton Resetare Selecție Nod
    if st.session_state["selected_id"]:
        if st.button("Înapoi la vedere generală"):
            st.session_state["selected_id"] = None
            st.rerun()

    # Detalii Nod Selectat
    selected_id = st.session_state["selected_id"]
    if selected_id and selected_id in nodes_data:
        info = nodes_data[selected_id]

        if info["type"] == "Partner":
            st.markdown(f'<div class="info-card"><b>Partener DSU</b><br>{info["label"]}</div>', unsafe_allow_html=True)
            
            ukr_text = "DA" if info["ukraine"] else "Nu"
            strat_text = "DA" if info["strategic"] else "Nu"

            c1, c2 = st.columns(2)
            c1.markdown(f'<div class="metric-box">Ucraina<br><b>{ukr_text}</b></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box">Strategic<br><b>{strat_text}</b></div>', unsafe_allow_html=True)

            st.markdown("<b>Domenii asociate:</b>", unsafe_allow_html=True)
            domains = [
                nodes_data[t]["label"]
                for s, t in edges_data
                if s == selected_id and nodes_data[t]["type"] == "Domain"
            ]
            if domains:
                for d in sorted(set(domains)):
                    st.markdown(f"- {d}")
            
            # Arătăm textul brut doar dacă e relevant
            # st.code(info["raw_domain"], language="text")

        else:  # Domain
            st.markdown(f'<div class="info-card"><b>Domeniu</b><br>{info["label"]}</div>', unsafe_allow_html=True)
            
            partners = [
                nodes_data[s]["label"]
                for s, t in edges_data
                if t == selected_id and nodes_data[s]["type"] == "Partner"
            ]
            st.markdown(f"Parteneri în domeniu: **{len(partners)}**")
            if partners:
                with st.expander("Vezi lista"):
                    for p in sorted(set(partners)):
                        st.markdown(f"- {p}")
    else:
        st.info("Selectează un nod din dreapta pentru detalii.")
        
    if missing_strategic:
         st.warning("Coloana 'Strategic' lipsește din CSV.")


# --- COLOANA DREAPTA: GRAF ---
with col_graph:
    st.markdown("### Ecosistem DSU")
    st.markdown(
        """
        <div style="margin-top: -10px; margin-bottom: 10px; font-size: 0.9rem; color: #a0a0a0;">
        Cercurile (Cyan/Galben) = Parteneri. Romburile (Roz) = Domenii. Trage de noduri pentru a rearanja.
        </div>
        """, 
        unsafe_allow_html=True
    )

    # 1. Calcul Grad (pentru mărime noduri)
    degree: dict[str, int] = {}
    for s, t in edges_data:
        degree[s] = degree.get(s, 0) + 1
        degree[t] = degree.get(t, 0) + 1

    # 2. Filtrare date pentru vizualizare
    # Regula: 
    # - Includem nodurile Domeniu selectate in filtru.
    # - Includem nodurile Partener care sunt conectate la cel putin un Domeniu selectat.
    
    visible_domain_ids = set()
    for nid, info in nodes_data.items():
        if info["type"] == "Domain" and info["label"] in selected_domains:
            visible_domain_ids.add(nid)
            
    visible_partner_ids = set()
    visible_edges_list = []
    
    for s, t in edges_data:
        # Presupunem s=Partener, t=Domeniu (bazat pe constructia din load_data)
        # Verificam daca t (Domeniul) este vizibil
        if t in visible_domain_ids:
            visible_partner_ids.add(s)
            visible_edges_list.append((s, t))

    # Construire Noduri Vizuale
    nodes_viz = []
    edges_viz = []

    # Culori
    COLOR_PARTNER = "#00f2c3"
    COLOR_STRATEGIC = "#ffd700"
    COLOR_DOMAIN = "#fd79a8"

    for nid in (visible_domain_ids | visible_partner_ids):
        info = nodes_data[nid]
        
        if info["type"] == "Partner":
            full_label = info["label"]
            display_label = full_label if len(full_label) <= 25 else full_label[:25] + "..."
            
            # Marime
            base_size = 14
            size = base_size + degree.get(nid, 1) * 0.4
            
            # Culoare
            color = COLOR_STRATEGIC if info.get("strategic") else COLOR_PARTNER
            
            nodes_viz.append(Node(
                id=nid,
                label=display_label,
                title=full_label,
                size=size,
                shape="dot",
                color=color,
                font={"color": "white", "size": 14}
            ))
        else: # Domain
            base_size = 26
            size = base_size + degree.get(nid, 1) * 0.9
            
            nodes_viz.append(Node(
                id=nid,
                label=info["label"],
                title=info["label"],
                size=size,
                shape="diamond",
                color=COLOR_DOMAIN,
                font={"color": "#ffeef6", "size": 14}
            ))

    for s, t in visible_edges_list:
        edges_viz.append(Edge(source=s, target=t, color="#2d3436", width=1.0))

    # 3. Configurare Graf
    config = Config(
        width=1200, # Ajustat pentru coloana
        height=800,
        directed=False,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A072",
        collapsible=True,
        physics_settings={
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.005,
                "springLength": 400,
                "springConstant": 0.03,
            },
            "minVelocity": 0.5,
            "solver": "forceAtlas2Based",
        },
    )

    # 4. Logica de Focus (Zoom pe un nod selectat)
    display_nodes = nodes_viz
    display_edges = edges_viz

    if st.session_state["selected_id"]:
        focus_id = st.session_state["selected_id"]
        
        # Filtram doar muchiile conectate la focus_id DINTRE cele deja vizibile (filtrate pe domenii)
        relevant_edges_viz = []
        for e in edges_viz:
            src = getattr(e, "source", None)
            trg = getattr(e, "target", getattr(e, "to", None))
            if src == focus_id or trg == focus_id:
                relevant_edges_viz.append(e)
        
        relevant_node_ids = {focus_id}
        for e in relevant_edges_viz:
            src = getattr(e, "source", None)
            trg = getattr(e, "target", getattr(e, "to", None))
            if src: relevant_node_ids.add(src)
            if trg: relevant_node_ids.add(trg)
        
        display_nodes = [n for n in nodes_viz if n.id in relevant_node_ids]
        display_edges = relevant_edges_viz

    # Randare
    clicked_id = agraph(nodes=display_nodes, edges=display_edges, config=config)
    
    if clicked_id is not None and clicked_id != st.session_state["selected_id"]:
        st.session_state["selected_id"] = clicked_id
        st.rerun()

    # --- EDITOR DATE (Jos, sub graf) ---
    st.divider()
    with st.expander("Editor Date"):
        st.write("Modifică datele și descarcă CSV-ul.")
        
        editable_df = df[["Partner", "Domain_Raw", "Ukraine", "Strategic"]].copy()
        
        edited_df = st.data_editor(
            editable_df, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "Partner": st.column_config.TextColumn("Partener"),
                "Domain_Raw": st.column_config.TextColumn("Domenii"),
                "Strategic": st.column_config.CheckboxColumn("Strategic?", default=False),
                "Ukraine": st.column_config.CheckboxColumn("Ucraina?", default=False)
            }
        )

        def convert_df(d):
            export = d.copy()
            export["Strategic"] = export["Strategic"].apply(lambda x: "da" if x else "")
            export["Ukraine"] = export["Ukraine"].apply(lambda x: "da" if x else "")
            return export.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="Descarcă CSV",
            data=convert_df(edited_df),
            file_name='data.csv',
            mime='text/csv',
        )