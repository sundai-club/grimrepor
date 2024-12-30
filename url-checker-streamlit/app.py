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

# Initialize session state for console output if it doesn't exist
if 'console_output' not in st.session_state:
    st.session_state.console_output = []

# Initialize session state for URL if it doesn't exist
if 'url_input' not in st.session_state:
    st.session_state.url_input = ""

# Example repository URL
EXAMPLE_REPO = "https://github.com/rjtshrm/point-normals-upsampling.git"

# Create columns for the URL input section
col1, col2 = st.columns([4, 1])

# Add empty space to align with the label
with col2:
    st.write("")  # This creates vertical space
    # Add "Use Example" button
    if st.button("Use Example"):
        st.session_state.url_input = EXAMPLE_REPO
        st.rerun()

with col1:
    # Create input field
    url = st.text_input("Enter GitHub Repository URL", 
                       value=st.session_state.url_input,
                       placeholder="https://github.com/username/repository")

# Create an expander for the console output
with st.expander("Console Output", expanded=True):
    console_output = st.empty()

def update_console(message: str):
    """Update the console output in Streamlit."""
    st.session_state.console_output.append(message)
    # Join all messages with newlines
    full_output = "\n".join(st.session_state.console_output)
    # Update the display
    console_output.text(full_output)

# Create check button
if st.button("Process Repository"):
    if url:
        # First check if it's a valid GitHub URL
        if check_url(url) == "correct":
            # Clear previous output
            st.session_state.console_output = []
            console_output.empty()
            
            with st.spinner("Processing repository..."):
                success, commit_url = process_repository(url, status_callback=update_console)
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