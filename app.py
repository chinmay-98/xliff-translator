import xml.etree.ElementTree as ET
from deep_translator import GoogleTranslator as Translator
from io import BytesIO
import streamlit as st
import time

def translate_text(text, translator):
    """Safely translate text with error handling and rate limiting"""
    if not text or text.strip() == "":
        return text
    try:
        # Add a small delay to avoid Google Translate rate limits
        time.sleep(0.5)
        return translator.translate(text)
    except Exception as e:
        st.warning(f"Translation error: {str(e)}")
        return text

def process_element_text(element, translator):
    """Process text content of an element and its children"""
    # Translate the element's text if it exists
    if element.text and element.text.strip():
        element.text = translate_text(element.text, translator)
    
    # Process all child elements
    for child in element:
        process_element_text(child, translator)
        
        # Translate the child's tail text if it exists
        if child.tail and child.tail.strip():
            child.tail = translate_text(child.tail, translator)

def translate_xliff(input_file, output_file, source_lang='auto', target_lang='en'):
    # Register the XLIFF namespace
    ET.register_namespace('', 'urn:oasis:names:tc:xliff:document:1.2')
    
    # Parse the XLIFF file
    tree = ET.parse(input_file)
    root = tree.getroot()
    
    # Initialize translator
    translator = Translator(source=source_lang, target=target_lang)
    
    # Track translation progress
    total_units = len(root.findall(".//{urn:oasis:names:tc:xliff:document:1.2}trans-unit"))
    progress_bar = st.progress(0)
    
    # Process all trans-unit elements
    for i, trans_unit in enumerate(root.findall(".//{urn:oasis:names:tc:xliff:document:1.2}trans-unit")):
        # Update progress
        progress_bar.progress((i + 1) / total_units)
        
        # Find source and target elements
        source = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}source')
        target = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}target')
        
        # Skip if no source
        if source is None:
            continue
            
        # Create target element if it doesn't exist
        if target is None:
            target = ET.SubElement(trans_unit, '{urn:oasis:names:tc:xliff:document:1.2}target')
        
        # Special handling for empty target elements or those without text
        if not target.text and len(target) == 0:
            # Deep copy the structure from source to target
            target_copy = ET.fromstring(ET.tostring(source))
            # Update the tag to be "target" if needed
            if target_copy.tag != '{urn:oasis:names:tc:xliff:document:1.2}target':
                target_copy.tag = '{urn:oasis:names:tc:xliff:document:1.2}target'
            
            # Replace the existing target with our copy
            trans_unit.remove(target)
            trans_unit.append(target_copy)
            target = target_copy
            
        # Now translate the content of the target element
        process_element_text(target, translator)
    
    # Write the modified tree to the output file
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    output_file.seek(0)

st.title("XLIFF Translator")
col1, col2 = st.columns([2,1])
container1 = col1.container(height=200)
container2 = col2.container(height=200)

language_codes = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "Arabic": "ar",
    "Portuguese": "pt",
    "Russian": "ru",
    "Ukrainian": "uk",
    "German": "de",
    "Chinese (Simplified)": "zh-CN",
    "Japanese": "ja"
}

source_lang = container2.selectbox("Source Language", list(language_codes.keys()))
target_lang = container2.selectbox("Target Language", list(language_codes.keys()))
uploaded_file = container1.file_uploader("Upload the XLIFF file you wish to convert", type=["xlf"])

if st.button("Translate"):
    if uploaded_file is not None:
        input_file_name = uploaded_file.name
        input_file = BytesIO(uploaded_file.read())
        output_file = BytesIO()
        source_lang_code = language_codes[source_lang]
        target_lang_code = language_codes[target_lang]
        
        with st.spinner('The conversion process has started... please wait, this may take several minutes for large files!'):
            if source_lang_code == target_lang_code:
                st.warning("**Warning:** Source and target language are selected as same!")
            translate_xliff(input_file, output_file, source_lang_code, target_lang_code)
        
        st.success("Translation complete! You can download the file now.", icon="✅")
        st.download_button(
            label="Download Translated XLIFF",
            data=output_file.getvalue(),
            file_name=f"{target_lang_code}_{input_file_name}",
            mime="application/octet-stream"
        )
    else:
        st.error("Please upload an XLIFF file.")
