import streamlit as st
from app.ui import pdf_uploader
from app.pdf_utils import extract_text_from_pdf
from app.vectorstore_utils import create_faiss_index, retrieve_relevant_docs
from app.chat_utils import get_chat_model, ask_chat_model
from app.config import EURI_API_KEY
from langchain_text_splitters import RecursiveCharacterTextSplitter
import time


st.set_page_config(
    page_title="MediChat Pro - Medical Document Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    :root {
        --neon-green: #00ff00;
        --neon-green-light: #00ff44;
        --neon-green-dark: #00cc00;
        --dark-bg: #0a0a0a;
        --dark-secondary: #1a1a1a;
    }
    
    body {
        background-color: var(--dark-bg);
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
        border-left: 3px solid var(--neon-green);
    }
    .chat-message.user {
        background-color: var(--dark-secondary);
        color: var(--neon-green);
        border-left-color: var(--neon-green-light);
    }
    .chat-message.assistant {
        background-color: var(--dark-secondary);
        color: var(--neon-green);
        border-left-color: var(--neon-green);
    }
    .chat-message .avatar {
        width: 2rem;
        height: 2rem;
        border-radius: 50%;
        margin-right: 0.5rem;
        background-color: var(--neon-green);
    }
    .chat-message .message {
        flex: 1;
    }
    .chat-message .timestamp {
        font-size: 0.8rem;
        opacity: 0.6;
        margin-top: 0.5rem;
        color: var(--neon-green-dark);
    }
    .stButton > button {
        background-color: var(--neon-green) !important;
        color: #000 !important;
        border-radius: 0.5rem;
        border: 2px solid var(--neon-green) !important;
        padding: 0.5rem 1rem;
        font-weight: bold;
        box-shadow: 0 0 10px var(--neon-green), inset 0 0 10px rgba(0, 255, 0, 0.3) !important;
    }
    .stButton > button:hover {
        background-color: var(--neon-green-light) !important;
        box-shadow: 0 0 20px var(--neon-green-light), inset 0 0 15px rgba(0, 255, 68, 0.5) !important;
    }
    .upload-section {
        background-color: var(--dark-secondary);
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border: 1px solid var(--neon-green);
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
    }
    .status-success {
        background-color: rgba(0, 255, 0, 0.1);
        color: var(--neon-green);
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
        border: 1px solid var(--neon-green);
    }
    h1, h2, h3 {
        color: var(--neon-green) !important;
        text-shadow: 0 0 10px var(--neon-green);
    }
</style>
""", unsafe_allow_html=True)


if "messages" not in st.session_state:
    st.session_state.messages = []
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "chat_model" not in st.session_state:
    st.session_state.chat_model = None
    
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="color: #00ff00; font-size: 3rem; margin-bottom: 0.5rem; text-shadow: 0 0 20px #00ff00;">🏥 MediChat Pro</h1>
    <p style="font-size: 1.2rem; color: #00ff00; margin-bottom: 2rem; text-shadow: 0 0 10px #00ff00;">Your Intelligent Medical Document Assistant</p>
</div>
""", unsafe_allow_html=True)

# Document upload section in main context
st.markdown("### 📁 Upload Medical Documents")
st.markdown("Upload your medical documents to start chatting!")

uploaded_files = pdf_uploader()

if uploaded_files:
    st.success(f"📄 {len(uploaded_files)} document(s) uploaded")
    
    # Process documents
    if st.button("🚀 Process Documents", type="primary"):
        with st.spinner("Processing your medical documents..."):
            # Extract text from all PDFs
            all_texts = []
            for file in uploaded_files:
                text = extract_text_from_pdf(file)
                all_texts.append(text)
            
            # Split texts into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
            )
            
            chunks = []
            for text in all_texts:
                chunks.extend(text_splitter.split_text(text))
            
            # Create FAISS index
            vectorstore = create_faiss_index(chunks)
            st.session_state.vectorstore = vectorstore
            
            # Initialize chat model
            chat_model = get_chat_model(EURI_API_KEY)
            st.session_state.chat_model = chat_model
            
            st.success("✅ Documents processed successfully!")
            st.balloons()

# Add a separator line
st.markdown("---")

# Main chat interface
st.markdown("### 💬 Chat with Your Medical Documents")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        st.caption(message["timestamp"])

# Chat input
if prompt := st.chat_input("Ask about your medical documents..."):
    # Add user message to chat history
    timestamp = time.strftime("%H:%M")
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt, 
        "timestamp": timestamp
    })
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(timestamp)
    
    # Generate response
    if st.session_state.vectorstore and st.session_state.chat_model:
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching documents..."):
                # Retrieve relevant documents
                relevant_docs = retrieve_relevant_docs(st.session_state.vectorstore, prompt)
                
                # Create context from relevant documents
                context = "\n\n".join([doc.page_content for doc in relevant_docs])
                
                # Create prompt with context
                system_prompt = f"""You are MediChat Pro, an intelligent medical document assistant. 
                Based on the following medical documents, provide accurate and helpful answers. 
                If the information is not in the documents, clearly state that.

                Medical Documents:
                {context}

                User Question: {prompt}

                Answer:"""
                
                response = ask_chat_model(st.session_state.chat_model, system_prompt)
            
            st.markdown(response)
            st.caption(timestamp)
            
            # Add assistant message to chat history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response, 
                "timestamp": timestamp
            })
    else:
        with st.chat_message("assistant"):
            st.error("⚠️ Please upload and process documents first!")
            st.caption(timestamp)    
