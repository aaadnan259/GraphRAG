"""
Streamlit Application Module
Provides web interface for document ingestion and Q&A chat.
"""

import asyncio
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import logging
from typing import List, Dict, Any

from config import config, ConfigurationError
from ingest import IngestionPipeline
from retriever import HybridRetriever
from models import QueryRequest
from database import get_read_graph, close_all_connections

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="GraphRAG Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def check_configuration():
    """Check if configuration is valid."""
    try:
        _ = config.google_api_key
        return True
    except ConfigurationError as e:
        st.error(f"Configuration Error: {e}")
        st.info(
            "Please create a `.env` file with the following variables:\n"
            "- GOOGLE_API_KEY\n"
            "- NEO4J_URI\n"
            "- NEO4J_RW_USER\n"
            "- NEO4J_RW_PASSWORD\n"
            "- NEO4J_RO_USER\n"
            "- NEO4J_RO_PASSWORD"
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


def inject_custom_css():
    """Inject custom CSS for modern SaaS dashboard look."""
    st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stButton > button { border-radius: 8px; font-weight: bold; border: none; transition: all 0.2s ease; }
        .stButton > button:hover { transform: scale(1.02); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        [data-testid="stFileUploader"] { border: 1px dashed #4A4A4A; border-radius: 10px; padding: 20px; }
        [data-testid="stMetric"] { background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333; }
        .empty-state { text-align: center; padding: 60px 20px; color: #666; }
        .empty-state-icon { font-size: 64px; opacity: 0.3; margin-bottom: 20px; }
        .empty-state-text { font-size: 18px; color: #888; }
    </style>
    """, unsafe_allow_html=True)


def render_hud():
    """Render heads-up display with key metrics."""
    try:
        retriever = get_retriever()
        stats = retriever.get_graph_statistics()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Entities", stats.get("total_entities", 0))

        with col2:
            st.metric("Total Relationships", stats.get("total_relationships", 0))

        with col3:
            system_status = "🟢 Online" if stats.get("total_entities", 0) > 0 else "🟡 Empty"
            st.metric("System Status", system_status)

    except Exception as e:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Entities", "N/A")
        with col2:
            st.metric("Total Relationships", "N/A")
        with col3:
            st.metric("System Status", "🔴 Error")


def render_sidebar():
    """Render sidebar with configuration and controls."""
    with st.sidebar:
        st.title("GraphRAG Engine")
        st.markdown("---")

        st.subheader("Configuration")
        st.text(f"LLM: {config.llm_model}")
        st.text(f"Embeddings: {config.embedding_model}")
        st.text(f"Chunk Size: {config.chunk_size}")

        st.markdown("---")

        try:
            retriever = get_retriever()
            stats = retriever.get_graph_statistics()

            if stats.get("entity_types"):
                with st.expander("Entity Types"):
                    for entity_type, count in list(stats["entity_types"].items())[:10]:
                        st.text(f"{entity_type}: {count}")

            if stats.get("relationship_types"):
                with st.expander("Relationship Types"):
                    for rel_type, count in list(stats["relationship_types"].items())[:10]:
                        st.text(f"{rel_type}: {count}")

        except Exception as e:
            pass

        st.markdown("---")

        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()


def render_graph_visualization():
    """Render knowledge graph visualization."""
    st.subheader("Knowledge Graph Visualization")

    try:
        retriever = get_retriever()
        driver = get_read_graph()

        with driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity)
                OPTIONAL MATCH (e)-[r]->(target:Entity)
                RETURN e.name as source, e.type as source_type,
                       type(r) as relationship, target.name as target
                LIMIT 100
                """
            )

            nodes_dict = {}
            edges = []

            for record in result:
                source = record["source"]
                source_type = record["source_type"]

                if source not in nodes_dict:
                    nodes_dict[source] = Node(
                        id=source,
                        label=source,
                        size=20,
                        title=f"{source} ({source_type})",
                    )

                if record["target"]:
                    target = record["target"]

                    if target not in nodes_dict:
                        nodes_dict[target] = Node(
                            id=target,
                            label=target,
                            size=20,
                        )

                    edges.append(
                        Edge(
                            source=source,
                            target=target,
                            label=record["relationship"],
                        )
                    )

            nodes = list(nodes_dict.values())

            if nodes:
                config_viz = Config(
                    width=800,
                    height=600,
                    directed=True,
                    physics=True,
                    hierarchical=False,
                )

                agraph(nodes=nodes, edges=edges, config=config_viz)
            else:
                # Modern empty state
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-state-icon">🕸️</div>
                    <div class="empty-state-text">No graph data available yet</div>
                    <div style="color: #666; font-size: 14px; margin-top: 10px;">
                        Upload a document in the Ingestion tab to get started
                    </div>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error rendering graph: {e}")


def render_ingestion_tab():
    """Render document ingestion interface."""
    st.header("Document Ingestion")

    st.caption("Upload text documents to extract entities, relationships, and build the knowledge graph. Supported formats: TXT, MD")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["txt", "md"],
        help="Upload a text document to ingest into the knowledge graph",
    )

    # Check file size limit (10MB)
    MAX_FILE_SIZE_MB = 10
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    if uploaded_file is not None and uploaded_file.size > MAX_FILE_SIZE_BYTES:
        st.error(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit. Please upload a smaller file.")
        uploaded_file = None

    col1, col2 = st.columns([1, 4])

    with col1:
        ingest_button = st.button("Ingest Document", type="primary", disabled=uploaded_file is None)

    if ingest_button and uploaded_file:
        with st.spinner("Processing document..."):
            try:
                text = uploaded_file.read().decode("utf-8")

                filename = uploaded_file.name

                pipeline = IngestionPipeline()

                pipeline.initialize_schema()

                result = asyncio.run(pipeline.ingest_document(text, filename))

                if result["success"]:
                    st.toast("Ingestion Complete!", icon='✅')
                    st.success(f"Document ingested successfully!")

                    st.json(result)

                    st.session_state.ingestion_history.append(result)

                    if st.session_state.retriever:
                        st.session_state.retriever = None

                else:
                    st.error(f"Ingestion failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error(f"Ingestion error: {e}")

                # Handle authentication errors specifically
                error_message = str(e)
                if "401" in error_message or "authentication" in error_message.lower() or "api key" in error_message.lower():
                    st.error("🔒 Authentication Failed: Please check your API Key.")
                else:
                    st.error(f"Error during ingestion: {e}")

    st.markdown("---")

    if st.session_state.ingestion_history:
        st.subheader("Ingestion History")

        for i, result in enumerate(reversed(st.session_state.ingestion_history)):
            with st.expander(f"{result['filename']} - {result.get('num_entities', 0)} entities"):
                st.json(result)

    st.markdown("---")

    render_graph_visualization()


def render_chat_tab():
    """Render chat interface for Q&A."""
    st.header("Ask Questions")

    st.markdown(
        """
        Ask questions about the ingested documents. The system uses hybrid retrieval
        combining vector search and knowledge graph traversal.
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        use_vector = st.checkbox("Use Vector Search", value=True)

    with col2:
        use_graph = st.checkbox("Use Graph Search", value=True)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant" and "sources" in message:
                with st.expander("View Sources"):
                    st.markdown("**Sources Used:**")
                    for source in message["sources"]:
                        st.markdown(f"- {source}")

                    if message.get("vector_context"):
                        st.markdown("**Vector Context:**")
                        for i, ctx in enumerate(message["vector_context"][:3]):
                            st.text_area(f"Context {i+1}", ctx, height=100, disabled=True)

    if prompt := st.chat_input("Ask a question about your documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    retriever = get_retriever()

                    request = QueryRequest(
                        query=prompt,
                        use_vector_search=use_vector,
                        use_graph_search=use_graph,
                    )

                    response = asyncio.run(retriever.retrieve(request))

                    st.markdown(response.answer)

                    with st.expander("View Sources"):
                        st.markdown("**Sources Used:**")
                        for source in response.sources:
                            st.markdown(f"- {source}")

                        if response.vector_context:
                            st.markdown("**Vector Context:**")
                            for i, ctx in enumerate(response.vector_context[:3]):
                                st.text_area(f"Context {i+1}", ctx, height=100, disabled=True)

                        if response.graph_context:
                            st.markdown("**Graph Context:**")
                            st.text_area("Graph Result", response.graph_context, height=100, disabled=True)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.answer,
                        "sources": response.sources,
                        "vector_context": response.vector_context,
                        "graph_context": response.graph_context,
                    })

                except Exception as e:
                    logger.error(f"Query error: {e}")
                    error_msg = f"Error processing query: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "sources": [],
                    })


def render_search_tab():
    """Render entity search interface."""
    st.header("Search Entities")

    st.markdown(
        """
        Search for specific entities in the knowledge graph.
        """
    )

    search_query = st.text_input("Search for entities by name:", placeholder="e.g., OpenAI, Microsoft")

    if search_query:
        try:
            retriever = get_retriever()
            entities = retriever.search_entities(search_query, limit=20)

            if entities:
                st.success(f"Found {len(entities)} matching entities:")

                for entity in entities:
                    with st.expander(f"{entity['name']} ({entity['type']})"):
                        st.markdown(f"**Type:** {entity['type']}")
                        st.markdown(f"**Description:** {entity.get('description', 'N/A')}")

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
                                st.markdown("**Relationships:**")
                                for rel, target in rels:
                                    st.markdown(f"- {rel} → {target}")

            else:
                st.info("No entities found matching your search.")

        except Exception as e:
            st.error(f"Search error: {e}")


def main():
    """Main application entry point."""
    if not check_configuration():
        return

    # Inject custom CSS for modern SaaS look
    inject_custom_css()

    initialize_session_state()

    render_sidebar()

    # Render HUD at the top of the page
    render_hud()

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Ingestion", "Chat", "Search"])

    with tab1:
        render_ingestion_tab()

    with tab2:
        render_chat_tab()

    with tab3:
        render_search_tab()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"Application error: {e}")
    finally:
        pass
