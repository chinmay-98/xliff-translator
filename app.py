import streamlit as st

# Import functionality modules
from xliff_translator import show_xliff_translator
from metadata_translator import show_metadata_translator  

# Set page configuration
st.set_page_config(
    page_title="Multi-Functionality Translation App",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define available functionalities
FUNCTIONALITIES = {
    "XLIFF Translator": show_xliff_translator,
    "Metadata Translator": show_metadata_translator,
    # Add more functionalities here as they are developed
}

# Main application
def main():
    # Sidebar for functionality selection
    with st.sidebar:
        st.title("Translation Tools")
        st.markdown("---")

        # Dropdown for selecting functionality
        selected_functionality = st.selectbox(
            "Select Tool:",
            options=list(FUNCTIONALITIES.keys()),
            index=0  # Default to first functionality
        )

        st.markdown("---")

        # Description based on selected functionality
        if selected_functionality == "XLIFF Translator":
            st.info("Translate XLIFF files between multiple languages.")
            st.markdown("**Supported formats:** .xlf")
        elif selected_functionality == "Metadata Translator":
            st.info("Translate metadata from Excel or CSV files into multiple languages.")
            st.markdown("**Supported formats:** .xlsx, .xls, .csv")

        # App info
        st.markdown("### About")
        st.markdown("This multi-functionality app provides translation tools for different file formats.")
        st.markdown("Version 1.1")

        # Footer
        st.markdown("---")
        st.markdown("<div style='text-align: center; color: gray;'>© 2023 Translation Tools</div>", unsafe_allow_html=True)

    # Load the selected functionality
    if selected_functionality in FUNCTIONALITIES:
        # Call the function associated with the selected functionality
        FUNCTIONALITIES[selected_functionality]()
    else:
        st.error(f"Functionality '{selected_functionality}' not found!")

# Run the app
if __name__ == "__main__":
    main()  
