import xml.etree.ElementTree as ET
from deep_translator import GoogleTranslator as Translator
from io import BytesIO
import streamlit as st
import time
import zipfile
from languages import language_codes

def translate_text(text, translator):
    """Safely translate text with error handling and minimal rate limiting"""
    if not text or text.strip() == "":
        return text
    try:
        # Reduced delay for faster processing - adjust if you encounter rate limits
        time.sleep(0.1)
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

def translate_xliff(input_file, source_lang, target_lang):
    """Translate an XLIFF file and return the translated content and time taken"""
    start_time = time.time()
    
    # Create a new BytesIO object for the output
    output_file = BytesIO()
    
    # Register the XLIFF namespace
    ET.register_namespace('', 'urn:oasis:names:tc:xliff:document:1.2')
    
    # Parse the XLIFF file
    tree = ET.parse(input_file)
    root = tree.getroot()
    
    # Initialize translator
    translator = Translator(source=source_lang, target=target_lang)
    
    # Process all trans-unit elements
    for trans_unit in root.findall(".//{urn:oasis:names:tc:xliff:document:1.2}trans-unit"):
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
    
    # Calculate time taken
    time_taken = round(time.time() - start_time, 2)
    
    return output_file, time_taken

st.title("Multi-Language XLIFF Translator")

col1, col2 = st.columns([2,1])
container1 = col1.container(height=200)
container2 = col2.container(height=200)

source_lang = container2.selectbox("Source Language", list(language_codes.keys()))

# Multi-select for target languages
target_langs = container2.multiselect(
    "Target Languages (Select Multiple)",
    options=list(language_codes.keys()),
    default=["Spanish"]  # Default selection
)

uploaded_file = container1.file_uploader("Upload the XLIFF file you wish to convert", type=["xlf"])

if st.button("Translate"):
    if uploaded_file is not None and target_langs:
        input_file_name = uploaded_file.name
        input_file_content = uploaded_file.read()
        source_lang_code = language_codes[source_lang]
        
        # Create result table
        result_table = []
        
        # For ZIP file creation
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # Process each target language
            with st.spinner(f'Translating to {len(target_langs)} languages...'):
                total_start_time = time.time()
                
                # Create a progress bar
                progress_bar = st.progress(0)
                
                for idx, target_lang_name in enumerate(target_langs):
                    # Update progress
                    progress_bar.progress((idx) / len(target_langs))
                    
                    target_lang_code = language_codes[target_lang_name]
                    
                    if source_lang_code == target_lang_code:
                        st.warning(f"**Warning:** Source and target language '{target_lang_name}' are the same! Skipping...")
                        continue
                    
                    # Process the file for this language
                    input_file = BytesIO(input_file_content)
                    status_text = st.empty()
                    status_text.text(f"Processing {target_lang_name}...")
                    
                    try:
                        translated_file, time_taken = translate_xliff(input_file, source_lang_code, target_lang_code)
                        
                        # Add file to ZIP
                        zip_file.writestr(f"{target_lang_code}_{input_file_name}", translated_file.getvalue())
                        
                        # Add result to table
                        result_table.append({
                            "Language": target_lang_name,
                            "Status": "✅ Success",
                            "Time": f"{time_taken} sec"
                        })
                    except Exception as e:
                        st.error(f"Error translating to {target_lang_name}: {str(e)}")
                        result_table.append({
                            "Language": target_lang_name,
                            "Status": "❌ Failed",
                            "Time": "N/A"
                        })
                
                # Complete progress bar
                progress_bar.progress(1.0)
                
                # Calculate total time
                total_time = round(time.time() - total_start_time, 2)
            
            # Add a summary file to the ZIP
            summary_content = "XLIFF Translation Summary\n"
            summary_content += f"Source language: {source_lang}\n"
            summary_content += f"Total time: {total_time} seconds\n\n"
            summary_content += "Language results:\n"
            for result in result_table:
                summary_content += f"- {result['Language']}: {result['Status']} ({result['Time']})\n"
            
            zip_file.writestr("translation_summary.txt", summary_content)
        
        # Display results in a table
        st.subheader("Translation Results")
        st.table(result_table)
        
        # Show total time
        st.info(f"Total processing time: {total_time} seconds")
        
        # Provide download button for ZIP file
        st.success("Translation complete! You can download all files as a ZIP archive.", icon="✅")
        st.download_button(
            label="Download All Translations (ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"xliff_translations_{source_lang_code}.zip",
            mime="application/zip"
        )
    elif not uploaded_file:
        st.error("Please upload an XLIFF file.")
    elif not target_langs:
        st.error("Please select at least one target language.")
