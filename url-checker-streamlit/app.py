import streamlit as st

def check_url(url):
    if "github" in url.lower():
        return "correct"
    return "incorrect"

# Set page title
st.set_page_config(page_title="URL Checker", page_icon="🔗")

# Add a title
st.title("URL Checker")

# Create input field
url = st.text_input("Enter URL", placeholder="Enter a URL to check")

# Create check button
if st.button("Check URL"):
    if url:
        result = check_url(url)
        
        # Display result with appropriate styling
        if result == "correct":
            st.success("✅ Correct! URL contains 'github'")
        else:
            st.error("❌ Incorrect! URL does not contain 'github'")
    else:
        st.warning("Please enter a URL")

# Add some information about the app
with st.expander("About this app"):
    st.write("""
    This app checks if a URL contains the word 'github'.
    - Enter any URL in the input field
    - Click the 'Check URL' button
    - The app will tell you if the URL contains 'github' or not
    """) 