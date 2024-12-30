import streamlit as st
import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.new_repo_manual import process_repository

def check_url(url):
    if "github.com" in url.lower():
        return "correct"
    return "incorrect"

# Set page config
st.set_page_config(page_title="Repository Checker", page_icon="🔗")

# Add title
st.title("Repository Checker and Fixer")

# Create input field
url = st.text_input("Enter GitHub Repository URL", placeholder="https://github.com/username/repository")

# Create check button
if st.button("Process Repository"):
    if url:
        # First check if it's a valid GitHub URL
        if check_url(url) == "correct":
            with st.spinner("Processing repository..."):
                success, commit_url = process_repository(url)
                if success:
                    st.success("✅ Repository processed successfully!")
                    # Display clickable commit link
                    st.markdown(f"""
                    ### Repository Fixed! 
                    👉 [Click here to view the changes]({commit_url})
                    
                    This link shows you exactly what was changed in the requirements file.
                    """)
                else:
                    st.error("❌ Failed to process repository")
        else:
            st.error("❌ Please enter a valid GitHub repository URL")
    else:
        st.warning("Please enter a repository URL")

# Add information about the app
with st.expander("About this app"):
    st.write("""
    This app processes GitHub repositories:
    1. Enter the URL of a GitHub repository
    2. Click 'Process Repository'
    3. The app will:
       - Clone the repository
       - Check and fix dependencies
       - Create a new fixed repository
       - Show you exactly what changes were made
    """) 