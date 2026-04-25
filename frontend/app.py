import streamlit as st
import requests
import os


def load_config(key, default):
    if key in os.environ:
        return os.environ[key]
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


API_URL = load_config("API_URL", "http://localhost:8000")
API_KEY = load_config("API_KEY", "change-me")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

LANES = {
    "All lanes": None,
    "Stocks": "stocks",
    "Macro": "macro",
    "Regulation": "regulation",
}

st.set_page_config(
    page_title="US Market Advisory",
    page_icon="📈",
    layout="wide",
)

st.title("📈 US Market Advisory")
st.caption(
    "Ask questions about US equities, macroeconomic indicators, and financial regulations."
)

with st.sidebar:
    st.header("Settings")
    lane_label = st.selectbox("Data lane", list(LANES.keys()))
    top_k = st.slider("Results to retrieve", min_value=1, max_value=20, value=8)
    show_citations = st.toggle("Show citations", value=True)
    show_metadata = st.toggle("Show metadata", value=False)

    st.divider()
    st.markdown("**Data lanes:**")
    st.markdown("- **Stocks** — US equities, ETFs, price series")
    st.markdown("- **Macro** — CPI, GDP, interest rates (FRED)")
    st.markdown("- **Regulation** — SEC filings, Federal Register")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citations"):
            with st.expander(f"📚 {len(msg['citations'])} source(s)"):
                for c in msg["citations"]:
                    st.markdown(f"**{c['source_title']}**")
                    if c["source_url"]:
                        st.markdown(f"[{c['source_url']}]({c['source_url']})")
                    st.caption(f"> {c['quote']}")
                    st.divider()
        if msg.get("metadata") and show_metadata:
            st.json(msg["metadata"])

query = st.chat_input("Ask about US markets, macro data, or regulations...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving and generating answer..."):
            try:
                response = requests.post(
                    f"{API_URL}/v1/query",
                    headers=HEADERS,
                    json={
                        "query": query,
                        "lane_hint": LANES[lane_label],
                        "top_k": top_k,
                        "include_citations": show_citations,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()

                answer = data.get("answer", "No answer returned.")
                citations = data.get("citations", [])
                metadata = data.get("metadata", {})

                st.markdown(answer)

                if citations and show_citations:
                    with st.expander(f"📚 {len(citations)} source(s)"):
                        for c in citations:
                            st.markdown(f"**{c['source_title']}**")
                            if c["source_url"]:
                                st.markdown(f"[{c['source_url']}]({c['source_url']})")
                            st.caption(f"> {c['quote']}")
                            st.divider()

                if show_metadata:
                    st.json(metadata)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "citations": citations if show_citations else [],
                        "metadata": metadata,
                    }
                )

            except requests.exceptions.Timeout:
                st.error("Request timed out. The model is taking too long — try again.")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to the API. Make sure the backend is running.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
