"""
GraphRAG Engine - Production-Grade Web Interface
Modern, professional UI with enhanced UX
"""

import asyncio
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config as GraphConfig
import logging
from typing import List, Dict, Any
import plotly.graph_objects as go
import plotly.express as px

from config import config, ConfigurationError
from ingest import IngestionPipeline
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

# Custom CSS for modern, professional look
def inject_professional_css():
    """Inject production-grade CSS styling"""
    st.markdown("""
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Global Styles */
        * {
            font-family: 'Inter', sans-serif;
        }

        /* Main container */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        /* Header styling */
        h1 {
            font-weight: 700;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        h2 {
            font-weight: 600;
            font-size: 1.8rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }

        h3 {
            font-weight: 600;
            font-size: 1.3rem;
            margin-bottom: 0.8rem;
        }

        /* Metrics cards */
        [data-testid="stMetricValue"] {
            font-size: 2.5rem;
            font-weight: 700;
        }

        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            padding: 1.5rem;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
        }

        /* Buttons */
        .stButton > button {
            border-radius: 12px;
            font-weight: 600;
            padding: 0.75rem 2rem;
            border: none;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
        }

        .stButton > button:active {
            transform: translateY(0);
        }

        /* File uploader */
        [data-testid="stFileUploader"] {
            border: 2px dashed #667eea;
            border-radius: 16px;
            padding: 2rem;
            background: rgba(102, 126, 234, 0.05);
            transition: all 0.3s ease;
        }

        [data-testid="stFileUploader"]:hover {
            border-color: #764ba2;
            background: rgba(118, 75, 162, 0.08);
        }

        /* Chat input */
        .stChatInput {
            border-radius: 12px;
        }

        /* Chat messages */
        [data-testid="stChatMessage"] {
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Expanders */
        .streamlit-expanderHeader {
            border-radius: 8px;
            font-weight: 600;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e1e2e 0%, #2a2a3e 100%);
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-color: transparent;
        }

        /* Success/Error messages */
        .stSuccess {
            border-radius: 12px;
            border-left: 4px solid #10b981;
        }

        .stError {
            border-radius: 12px;
            border-left: 4px solid #ef4444;
        }

        .stInfo {
            border-radius: 12px;
            border-left: 4px solid #3b82f6;
        }

        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            border: 2px dashed rgba(255, 255, 255, 0.1);
        }

        .empty-state-icon {
            font-size: 4rem;
            opacity: 0.4;
            margin-bottom: 1rem;
        }

        .empty-state-text {
            font-size: 1.2rem;
            color: #888;
            margin-bottom: 0.5rem;
        }

        .empty-state-subtext {
            font-size: 0.95rem;
            color: #666;
        }

        /* Stats badge */
        .stat-badge {
            display: inline-block;
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
            border: 1px solid rgba(102, 126, 234, 0.3);
            font-size: 0.85rem;
            font-weight: 600;
            margin: 0.2rem;
        }

        /* Code blocks */
        code {
            border-radius: 6px;
            padding: 0.2rem 0.4rem;
            background: rgba(255, 255, 255, 0.1);
        }

        /* JSON viewer */
        .stJson {
            border-radius: 12px;
            background: rgba(0, 0, 0, 0.3);
        }
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

def initialize_session_state():
    """Initialize Streamlit session state."""
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

def render_header():
    """Render professional header with branding"""
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("# 🧠 GraphRAG Engine")
        st.caption("Production-Grade Knowledge Graph & RAG System powered by Gemini AI")

    with col2:
        try:
            retriever = get_retriever()
            stats = retriever.get_graph_statistics()
            total = stats.get("total_entities", 0) + stats.get("total_relationships", 0)
            if total > 0:
                st.success(f"✅ **{total}** nodes in graph", icon="🎯")
            else:
                st.info("🌱 Ready to ingest", icon="📥")
        except:
            st.warning("⚠️ Initializing...", icon="⏳")

def render_metrics_dashboard():
    """Render modern metrics dashboard"""
    try:
        retriever = get_retriever()
        stats = retriever.get_graph_statistics()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            entities = stats.get("total_entities", 0)
            st.metric(
                label="📊 Entities",
                value=f"{entities:,}",
                delta=f"+{entities}" if entities > 0 else None
            )

        with col2:
            relationships = stats.get("total_relationships", 0)
            st.metric(
                label="🔗 Relationships",
                value=f"{relationships:,}",
                delta=f"+{relationships}" if relationships > 0 else None
            )

        with col3:
            entity_types = len(stats.get("entity_types", {}))
            st.metric(
                label="🏷️ Entity Types",
                value=entity_types
            )

        with col4:
            rel_types = len(stats.get("relationship_types", {}))
            st.metric(
                label="⚡ Relation Types",
                value=rel_types
            )

        # Additional stats in expander
        if entity_types > 0:
            with st.expander("📈 Detailed Statistics", expanded=False):
                col_a, col_b = st.columns(2)

                with col_a:
                    st.markdown("**Top Entity Types**")
                    entity_types_dict = stats.get("entity_types", {})
                    for et, count in list(entity_types_dict.items())[:5]:
                        st.markdown(f"<div class='stat-badge'>{et}: {count}</div>", unsafe_allow_html=True)

                with col_b:
                    st.markdown("**Top Relationship Types**")
                    rel_types_dict = stats.get("relationship_types", {})
                    for rt, count in list(rel_types_dict.items())[:5]:
                        st.markdown(f"<div class='stat-badge'>{rt}: {count}</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Unable to fetch statistics: {e}")

def render_sidebar():
    """Render modern sidebar"""
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")

        with st.expander("🤖 AI Settings", expanded=True):
            st.code(f"Model: {config.llm_model}", language="text")
            st.code(f"Embeddings: {config.embedding_model}", language="text")

        with st.expander("🔧 Processing Settings"):
            st.code(f"Chunk Size: {config.chunk_size}", language="text")
            st.code(f"Chunk Overlap: {config.chunk_overlap}", language="text")
            st.code(f"Vector Search K: {config.vector_search_k}", language="text")

        st.markdown("---")

        st.markdown("### 🎯 Quick Actions")

        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        if st.button("🔄 Refresh Stats", use_container_width=True):
            st.session_state.retriever = None
            st.rerun()

        st.markdown("---")

        st.markdown("### 📚 Resources")
        st.markdown("[📖 Documentation](README.md)")
        st.markdown("[🚀 Quick Start](QUICK_START.md)")
        st.markdown("[🔒 Security Guide](test_security.py)")

def render_ingestion_tab():
    """Render modern ingestion interface"""
    st.markdown("## 📥 Document Ingestion")
    st.markdown("Upload documents to extract entities, relationships, and build your knowledge graph.")

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "**Choose a file**",
            type=["txt", "md"],
            help="Upload text or markdown documents (max 10MB)",
            label_visibility="collapsed"
        )

        if uploaded_file:
            st.success(f"✅ **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")

    with col2:
        st.markdown("**Supported Formats:**")
        st.markdown("- 📄 `.txt` - Plain text")
        st.markdown("- 📝 `.md` - Markdown")

    # File size check
    MAX_FILE_SIZE_MB = 10
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    if uploaded_file and uploaded_file.size > MAX_FILE_SIZE_BYTES:
        st.error(f"❌ File exceeds {MAX_FILE_SIZE_MB}MB limit. Please upload a smaller file.")
        uploaded_file = None

    # Ingest button
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    with col_btn1:
        ingest_button = st.button(
            "🚀 Ingest Document",
            type="primary",
            disabled=uploaded_file is None,
            use_container_width=True
        )

    if ingest_button and uploaded_file:
        with st.spinner("🔄 Processing document with Gemini AI..."):
            try:
                text = uploaded_file.read().decode("utf-8")
                filename = uploaded_file.name

                pipeline = IngestionPipeline()
                pipeline.initialize_schema()

                # Progress indicator
                progress_bar = st.progress(0)
                status_text = st.empty()

                status_text.text("📊 Splitting document into chunks...")
                progress_bar.progress(20)

                status_text.text("🤖 Extracting entities with Gemini AI...")
                progress_bar.progress(40)

                result = asyncio.run(pipeline.ingest_document(text, filename))

                progress_bar.progress(100)
                status_text.empty()
                progress_bar.empty()

                if result["success"]:
                    st.balloons()
                    st.success("🎉 **Document ingested successfully!**")

                    # Results in columns
                    res_col1, res_col2, res_col3 = st.columns(3)

                    with res_col1:
                        st.metric("📦 Chunks", result['num_chunks'])
                    with res_col2:
                        st.metric("📊 Entities", result['num_entities'])
                    with res_col3:
                        st.metric("🔗 Relationships", result['num_relationships'])

                    with st.expander("🔍 View Details"):
                        st.json(result)

                    st.session_state.ingestion_history.append(result)

                    if st.session_state.retriever:
                        st.session_state.retriever = None
                else:
                    st.error(f"❌ **Ingestion failed:** {result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error(f"Ingestion error: {e}")
                if "401" in str(e) or "api key" in str(e).lower():
                    st.error("🔒 **Authentication Failed**: Please check your Google API Key in `.env`")
                else:
                    st.error(f"❌ **Error:** {str(e)}")

    st.markdown("---")

    # Ingestion history
    if st.session_state.ingestion_history:
        st.markdown("### 📜 Ingestion History")

        for i, result in enumerate(reversed(st.session_state.ingestion_history)):
            with st.expander(f"📄 {result['filename']} - **{result.get('num_entities', 0)}** entities", expanded=(i == 0)):
                col_h1, col_h2, col_h3 = st.columns(3)
                with col_h1:
                    st.metric("Chunks", result.get('num_chunks', 0))
                with col_h2:
                    st.metric("Entities", result.get('num_entities', 0))
                with col_h3:
                    st.metric("Relationships", result.get('num_relationships', 0))

                if st.checkbox("🔍 Show Raw Data", key=f"raw_{i}"):
                    st.json(result)
    else:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-state-icon'>📭</div>
            <div class='empty-state-text'>No documents ingested yet</div>
            <div class='empty-state-subtext'>Upload a document above to get started</div>
        </div>
        """, unsafe_allow_html=True)

def render_chat_tab():
    """Render modern chat interface"""
    st.markdown("## 💬 Ask Questions")
    st.markdown("Query your knowledge graph using natural language. The system uses hybrid retrieval (vector + graph).")

    st.markdown("---")

    # Search options
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        use_vector = st.checkbox("🔍 Vector Search", value=True)

    with col2:
        use_graph = st.checkbox("🕸️ Graph Search", value=True)

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant" and "sources" in message:
                with st.expander("📚 View Sources & Context"):
                    st.markdown("**🎯 Sources Used:**")
                    for source in message["sources"]:
                        st.markdown(f"- ✅ {source}")

                    if message.get("vector_context"):
                        st.markdown("**📄 Vector Context:**")
                        for i, ctx in enumerate(message["vector_context"][:2], 1):
                            st.text_area(f"Context {i}", ctx, height=100, disabled=True, key=f"ctx_{i}_{len(st.session_state.messages)}")

    # Chat input
    if prompt := st.chat_input("💭 Ask anything about your documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    retriever = get_retriever()

                    request = QueryRequest(
                        query=prompt,
                        use_vector_search=use_vector,
                        use_graph_search=use_graph,
                    )

                    response = asyncio.run(retriever.retrieve(request))

                    st.markdown(response.answer)

                    with st.expander("📚 View Sources & Context"):
                        st.markdown("**🎯 Sources Used:**")
                        for source in response.sources:
                            st.markdown(f"- ✅ {source}")

                        if response.vector_context:
                            st.markdown("**📄 Vector Context:**")
                            for i, ctx in enumerate(response.vector_context[:2], 1):
                                st.text_area(f"Context {i}", ctx, height=100, disabled=True, key=f"new_ctx_{i}")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.answer,
                        "sources": response.sources,
                        "vector_context": response.vector_context,
                    })

                except Exception as e:
                    logger.error(f"Query error: {e}")
                    error_msg = f"❌ **Error:** {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "sources": [],
                    })

    # Empty state
    if not st.session_state.messages:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-state-icon'>💬</div>
            <div class='empty-state-text'>No messages yet</div>
            <div class='empty-state-subtext'>Start a conversation by typing a question below</div>
        </div>
        """, unsafe_allow_html=True)

def render_search_tab():
    """Render modern entity search interface"""
    st.markdown("## 🔍 Entity Search")
    st.markdown("Search and explore entities in your knowledge graph.")

    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "Search entities",
            placeholder="e.g., TechVision, Sarah Chen, San Francisco...",
            label_visibility="collapsed"
        )

    with col2:
        search_limit = st.selectbox("Results", [10, 20, 50], index=0)

    if search_query:
        try:
            retriever = get_retriever()
            entities = retriever.search_entities(search_query, limit=search_limit)

            if entities:
                st.success(f"✅ Found **{len(entities)}** matching entities")

                for entity in entities:
                    with st.expander(f"📌 **{entity['name']}** ({entity['type']})", expanded=False):
                        col_e1, col_e2 = st.columns([2, 1])

                        with col_e1:
                            st.markdown(f"**Type:** `{entity['type']}`")
                            if entity.get('description'):
                                st.markdown(f"**Description:** {entity['description']}")

                        with col_e2:
                            st.markdown("**Quick Info:**")
                            st.info(f"Type: {entity['type']}", icon="🏷️")

                        # Show relationships
                        driver = get_read_graph()
                        with driver.session() as session:
                            rels = session.run(
                                """
                                MATCH (e:Entity {name: $name})-[r]->(target)
                                RETURN type(r) as relationship, target.name as target
                                LIMIT 10
                                """,
                                name=entity['name']
                            ).values()

                            if rels:
                                st.markdown("**🔗 Relationships:**")
                                for rel, target in rels:
                                    st.markdown(f"- `{rel}` → **{target}**")
            else:
                st.info("🔍 No entities found. Try a different search term.")

        except Exception as e:
            st.error(f"❌ Search error: {str(e)}")
    else:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-state-icon'>🔍</div>
            <div class='empty-state-text'>Enter a search term above</div>
            <div class='empty-state-subtext'>Search for entities by name, type, or description</div>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main application entry point"""
    if not check_configuration():
        return

    inject_professional_css()
    initialize_session_state()

    render_header()

    st.markdown("---")

    render_metrics_dashboard()

    st.markdown("---")

    render_sidebar()

    tab1, tab2, tab3 = st.tabs(["📥 Ingestion", "💬 Chat", "🔍 Search"])

    with tab1:
        render_ingestion_tab()

    with tab2:
        render_chat_tab()

    with tab3:
        render_search_tab()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.85rem; padding: 1rem 0;'>
        <strong>GraphRAG Engine</strong> • Powered by Gemini AI & Neo4j • Built with ❤️
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"❌ Application error: {str(e)}")
