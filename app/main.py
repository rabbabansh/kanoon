import streamlit as st
from io import StringIO

st.header("Semantic Search Engine for Documents and Q&A")
query = st.text_input("Enter your question")

button = st.button("Submit")

if button:
    st.success("Search Results:")
