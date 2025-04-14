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

def process_element_text(element, translator, progress_callback=None):
    """Process text content of an element and its children"""
    # Translate the element's text if it exists
    if element.text and element.text.strip():
        element.text = translate_text(element.text, translator)
        if progress_callback:
            progress_callback()
    
    # Process all child elements
    for child in element:
        process_element_text(child, translator, progress_callback)
        
        # Translate the child's tail text if it exists
        if child.tail and child.tail.strip():
            child.tail = translate_text(child.tail, translator)
            if progress_callback:
                progress_callback()

def translate_xliff(input_file, source_lang, target_lang, progress_callback=None):
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
    
    # Count total trans-units to calculate progress
    trans_units = root.findall(".//{urn:oasis:names:tc:xliff:document:1.2}trans-unit")
    total_units = len(trans_units)
    completed_units = 0
    
    # Process all trans-unit elements
    for trans_unit in trans_units:
        # Find source and target elements
        source = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}source')
        target = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}target')
        
        # Skip if no source
        if source is None:
            completed_units += 1
            if progress_callback:
                progress_callback(completed_units / total_units)
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
            
        # Define a local progress updater for text elements
        def update_progress_within_unit():
            # This intentionally doesn't update the overall progress to avoid too many updates
            pass
            
        # Now translate the content of the target element
        process_element_text(target, translator, update_progress_within_unit)
        
        # Update progress after each trans-unit is processed
        completed_units += 1
        if progress_callback:
            progress_callback(completed_units / total_units)
    
    # Write the modified tree to the output file
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    output_file.seek(0)
    
    # Calculate time taken
    time_taken = round(time.time() - start_time, 2)
    
    return output_file, time_taken

def show_xliff_translator():
    """Main function to display and run the XLIFF translator interface"""
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
            
            # Initialize containers for showing progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Calculate progress segments for each language
            num_languages = len(target_langs)
            segment_size = 1.0 / num_languages
            current_segment = 0
            
            # Process each target language
            total_start_time = time.time()
            
            # For single language translation
            single_file_data = None
            single_file_name = None
            
            # For multiple language translations
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for idx, target_lang_name in enumerate(target_langs):
                    target_lang_code = language_codes[target_lang_name]
                    
                    # Update status text for the current language
                    status_text.text(f"Processing {target_lang_name}... ({idx+1}/{len(target_langs)})")
                    
                    if source_lang_code == target_lang_code:
                        st.warning(f"**Warning:** Source and target language '{target_lang_name}' are the same! Skipping...")
                        current_segment += segment_size
                        progress_bar.progress(current_segment)
                        continue
                    
                    # Process the file for this language
                    input_file = BytesIO(input_file_content)
                    
                    # Define a progress callback for this language segment
                    def update_progress(file_progress=0):
                        # Calculate overall progress: completed segments + progress within current segment
                        overall_progress = current_segment + (file_progress * segment_size)
                        progress_bar.progress(min(overall_progress, 1.0))  # Ensure we don't exceed 100%
                    
                    try:
                        translated_file, time_taken = translate_xliff(
                            input_file, 
                            source_lang_code, 
                            target_lang_code, 
                            update_progress
                        )
                        
                        # For single file download
                        if len(target_langs) == 1:
                            single_file_data = translated_file.getvalue()
                            single_file_name = f"{target_lang_code}_{input_file_name}"
                        else:
                            # Add file to ZIP for multiple languages
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
                    
                    # Move to the next segment
                    current_segment += segment_size
                    progress_bar.progress(min(current_segment, 1.0))
                
                # Only add summary to ZIP if we have multiple languages
                if len(target_langs) > 1:
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
            
            # Complete progress
            status_text.text("Translation complete!")
            progress_bar.progress(1.0)
            
            # Calculate and display total time
            total_time = round(time.time() - total_start_time, 2)
            st.info(f"Total processing time: {total_time} seconds")
            
            # Display results in a table
            st.subheader("Translation Results")
            st.table(result_table)
            
            # Provide download options based on number of languages
            st.success("Translation complete! You can download your file(s) below.", icon="✅")
            
            if len(target_langs) == 1 and single_file_data:
                # Direct file download for single language
                st.download_button(
                    label=f"Download {target_langs[0]} Translation",
                    data=single_file_data,
                    file_name=single_file_name,
                    mime="application/x-xliff+xml"
                )
            else:
                # ZIP download for multiple languages
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
