"""
GraphRAG Engine
"""

import asyncio
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config as GraphConfig
import logging
from typing import List, Dict, Any
import plotly.graph_objects as go
import plotly.express as px

from config import config, ConfigurationError
from ingest import Ingestor
from retriever import HybridRetriever
from models import QueryRequest
from database import get_read_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="GraphRAG Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Styles
def load_css():
    st.markdown("""
    <style>
        .block-container { padding-top: 2rem; max-width: 1400px; }
        h1 { font-size: 2.5rem; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .stMetric { background: #f0f2f6; padding: 1rem; border-radius: 10px; }
        .stButton button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

def check_configuration():
    """Check if configuration is valid."""
    try:
        _ = config.google_api_key
        return True
    except ConfigurationError as e:
        st.error(f"⚠️ Configuration Error: {e}")
        st.info(
            """
            **Setup Required:**
            Create a `.env` file with:
            - `GOOGLE_API_KEY`
            - `NEO4J_URI`
            - `NEO4J_RW_USER` / `NEO4J_RW_PASSWORD`
            - `NEO4J_RO_USER` / `NEO4J_RO_PASSWORD`
            """
        )
        return False

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "ingestion_history" not in st.session_state:
        st.session_state.ingestion_history = []
    if "retriever" not in st.session_state:
        st.session_state.retriever = None

def get_retriever() -> HybridRetriever:
    """Get or create retriever instance."""
    if st.session_state.retriever is None:
        st.session_state.retriever = HybridRetriever()
    return st.session_state.retriever

def header():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("# 🧠 GraphRAG Engine")
    with col2:
        try:
            r = get_retriever()
            stats = r.get_graph_statistics()
            total = stats.get("total_entities", 0) + stats.get("total_relationships", 0)
            if total > 0:
                st.success(f"{total} nodes", icon="🎯")
            else:
                st.info("Ready", icon="📥")
        except:
            st.warning("Loading...", icon="⏳")

def show_stats():
    try:
        r = get_retriever()
        stats = r.get_graph_statistics()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entities", stats.get("total_entities", 0))
        c2.metric("Relationships", stats.get("total_relationships", 0))
        c3.metric("Entity Types", len(stats.get("entity_types", {})))
        c4.metric("Rel Types", len(stats.get("relationship_types", {})))

    except Exception as e:
        st.error(f"Stats error: {e}")

def sidebar():
    with st.sidebar:
        st.markdown("### Configuration")
        with st.expander("Settings", expanded=True):
            st.text(f"Model: {config.llm_model}")
            st.text(f"Embeddings: {config.embedding_model}")

        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

        if st.button("Refresh Stats"):
            st.session_state.retriever = None
            st.rerun()
            
        st.markdown("---")
        st.markdown("[Documentation](README.md)")

def ingest_ui():
    st.markdown("## Ingestion")
    
    uploaded = st.file_uploader("Upload document", type=["txt", "md"])
    if uploaded and st.button("Ingest"):
        with st.spinner("Processing..."):
            try:
                text = uploaded.read().decode("utf-8")
                
                ingestor = Ingestor()
                ingestor.init_schema()
                
                result = asyncio.run(ingestor.ingest(text, uploaded.name))
                
                if result["success"]:
                    st.success("Ingested!")
                    st.json(result)
                    st.session_state.ingestion_history.append(result)
                    st.session_state.retriever = None
                else:
                    st.error(f"Failed: {result.get('error')}")
                    
            except Exception as e:
                st.error(f"Error: {e}")

    if st.session_state.ingestion_history:
        st.markdown("### History")
        for i, res in enumerate(reversed(st.session_state.ingestion_history)):
            with st.expander(f"{res['filename']} ({res.get('num_entities', 0)} entities)"):
                st.json(res)

def chat_ui():
    st.markdown("## Chat")
    
    col1, col2 = st.columns([1, 1])
    use_vector = col1.checkbox("Vector Search", value=True)
    use_graph = col2.checkbox("Graph Search", value=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for s in msg["sources"]:
                        st.markdown(f"- {s}")

    if prompt := st.chat_input("Ask question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    r = get_retriever()
                    req = QueryRequest(query=prompt, use_vector_search=use_vector, use_graph_search=use_graph)
                    resp = asyncio.run(r.retrieve(req))
                    
                    st.markdown(resp.answer)
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": resp.answer,
                        "sources": resp.sources
                    })
                except Exception as e:
                    st.error(f"Error: {e}")

def search_ui():
    st.markdown("## Entity Search")
    
    query = st.text_input("Search entities")
    if query:
        try:
            r = get_retriever()
            ents = r.search_entities(query)
            if ents:
                st.write(f"Found {len(ents)} entities:")
                for e in ents:
                    with st.expander(f"{e['name']} ({e['type']})"):
                        st.write(e.get('description', 'No desc'))
            else:
                st.info("No matches")
        except Exception as e:
            st.error(f"Error: {e}")

def main():
    if not check_configuration():
        return

    load_css()
    init_session()

    header()
    show_stats()
    sidebar()

    t1, t2, t3 = st.tabs(["Ingestion", "Chat", "Search"])
    
    with t1: ingest_ui()
    with t2: chat_ui()
    with t3: search_ui()

if __name__ == "__main__":
    main()
