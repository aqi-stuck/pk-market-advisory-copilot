import streamlit as st
import requests
import os

st.set_page_config(page_title="US Market Advisory Copilot", page_icon="📈")

st.title("📈 US Market Advisory Copilot")
st.markdown("Ask questions about US equities, macroeconomics, or regulations.")

# Configuration - these should be set in Streamlit Cloud Secrets
# Use st.secrets to securely access variables from .streamlit/secrets.toml
try:
    API_BASE_URL = st.secrets.get(
        "API_BASE_URL", os.environ.get("API_URL", "http://localhost:8000")
    )
    API_KEY = st.secrets.get("API_KEY", "")
except Exception:
    # Fallback if st.secrets is not initialized (e.g., missing secrets.toml or Cloud config)
    API_BASE_URL = os.environ.get("API_URL", "http://localhost:8000")
    API_KEY = ""

# If API_KEY is not set in secrets, allow user to input it in sidebar
if not API_KEY:
    API_KEY = st.sidebar.text_input(
        "Enter API Bearer Token",
        type="password",
        help="The Bearer token configured in your backend Settings.",
    )
else:
    st.sidebar.success("API Key loaded from secrets.")

top_k = st.sidebar.slider("Results to retrieve", min_value=1, max_value=20, value=8)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "citations" in message:
            with st.expander("Sources"):
                for cite in message["citations"]:
                    st.write(f"- **{cite['source_title']}**: {cite['quote']}")

# Chat input
if prompt := st.chat_input("What would you like to know?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing market data..."):
            try:
                if not API_KEY or not API_BASE_URL:
                    st.error(
                        "Configuration Missing: Please provide a valid API URL and Bearer Token in the sidebar or secrets.toml."
                    )
                    st.stop()  # Stop execution if critical config is missing

                headers = {"Authorization": f"Bearer {API_KEY}"}
                payload = {"query": prompt, "top_k": top_k}
                response = requests.post(
                    f"{API_BASE_URL}/v1/query",
                    json=payload,
                    headers=headers,
                    timeout=90,
                )
                response.raise_for_status()
                data = response.json()

                answer = data["answer"]
                citations = data.get("citations", [])

                st.markdown(answer)
                if citations:
                    with st.expander("Sources"):
                        for cite in citations:
                            st.write(f"- **{cite['source_title']}**: {cite['quote']}")

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "citations": citations}
                )
            except Exception as e:
                st.error(f"Error connecting to API: {str(e)}")

st.sidebar.markdown("---")
st.sidebar.info(
    "This system uses a RAG architecture to provide grounded financial insights. "
    "Always verify critical information with primary sources."
)
