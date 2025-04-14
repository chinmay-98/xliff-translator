import streamlit as st
import pandas as pd
import time
from io import BytesIO
from deep_translator import GoogleTranslator as Translator
from languages import language_codes

def translate_text(text, translator):
    """Safely translate text with error handling and minimal rate limiting"""
    if not text or pd.isna(text) or str(text).strip() == "":
        return text

    # Convert to string if not already
    text_str = str(text)

    # Check if text is likely an abbreviation (all caps, short)
    if text_str.isupper() and len(text_str) <= 10 and ' ' not in text_str:
        # For abbreviations, we'll return as is
        return text_str

    # Check if text is a time format (e.g., "1 hr 30 min")
    if any(time_unit in text_str.lower() for time_unit in [' hr', ' min', ' sec', ' day', ' week', ' month']):
        # For time formats, we'll return as is
        return text_str

    # Check if text contains path-like structures with '>' symbols
    if ' > ' in text_str and text_str.count('>') >= 1:
        # Split by '>' and translate each part separately
        parts = text_str.split(' > ')
        translated_parts = []

        for part in parts:
            try:
                time.sleep(0.1)  # Rate limiting
                translated_part = translator.translate(part.strip())
                translated_parts.append(translated_part)
            except Exception as e:
                st.warning(f"Translation error for part '{part}': {str(e)}")
                translated_parts.append(part)  # Keep original if translation fails

        # Rejoin with the same separator
        return ' > '.join(translated_parts)

    # Check if text contains comma-separated items that might be roles or categories
    if ',' in text_str and all(len(item.strip()) < 20 for item in text_str.split(',')):
        # Split by comma and translate each part separately
        parts = text_str.split(',')
        translated_parts = []

        for part in parts:
            try:
                time.sleep(0.1)  # Rate limiting
                translated_part = translator.translate(part.strip())
                translated_parts.append(translated_part)
            except Exception as e:
                st.warning(f"Translation error for part '{part}': {str(e)}")
                translated_parts.append(part)  # Keep original if translation fails

        # Rejoin with the same separator
        return ', '.join(translated_parts)

    # Standard translation for other text
    try:
        # Reduced delay for faster processing - adjust if you encounter rate limits
        time.sleep(0.1)
        return translator.translate(text_str)
    except Exception as e:
        st.warning(f"Translation error: {str(e)}")
        return text_str

def process_metadata_file(file, source_lang_code, target_lang_codes, progress_callback=None):
    """Process the metadata file and translate the values"""
    start_time = time.time()

    # Determine file type and read accordingly
    try:
        if file.name.endswith('.csv'):
            # Read CSV with all columns as string type
            df = pd.read_csv(file, dtype=str)
        elif file.name.endswith(('.xlsx', '.xls')):
            # Read Excel with all columns as string type
            df = pd.read_excel(file, dtype=str)
        else:
            raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}. Please check the file format.")

    # Check if file has at least 2 columns
    if df.shape[1] < 2:
        raise ValueError("File must have at least 2 columns: field names and values.")

    # Create a copy of the dataframe to work with
    result_df = df.copy()

    # Convert all values to string to ensure proper handling
    for col in df.columns:
        df[col] = df[col].astype(str)
        result_df[col] = result_df[col].astype(str)

    # Get the values from the second column that need translation
    # Skip the first row if it's a header
    values_to_translate = df.iloc[1:, 1].tolist() if df.shape[0] > 1 else []
    total_values = len(values_to_translate)

    # Create result table for tracking translations
    result_table = []

    # Process each target language
    for idx, target_lang_code in enumerate(target_lang_codes):
        # Skip if source and target are the same
        if source_lang_code == target_lang_code:
            result_table.append({
                "Language": next((k for k, v in language_codes.items() if v == target_lang_code), target_lang_code),
                "Status": "⚠️ Skipped (Same as source)",
                "Time": "N/A"
            })
            continue

        lang_start_time = time.time()

        # Initialize translator
        translator = Translator(source=source_lang_code, target=target_lang_code)

        # Get language name for column header
        target_lang_name = next((k for k, v in language_codes.items() if v == target_lang_code), target_lang_code)

        # Create a new column for this language with the same header as the source column

        # First, copy the header row (first row) as is
        if df.shape[0] > 0:
            # Get the original header from the second column
            header_value = df.iloc[0, 1] if df.shape[0] > 0 else ""

            # Try to translate the header if it's not empty
            if header_value and str(header_value).strip():
                try:
                    translated_header = translator.translate(str(header_value))
                except Exception:
                    translated_header = header_value  # Keep original if translation fails
            else:
                translated_header = header_value

        # Prepare translated values list
        translated_values = []

        # If we have a header row, add the translated header as the first element
        if df.shape[0] > 0:
            translated_values.append(translated_header)

        # Translate each value (skipping header row)
        for i, value in enumerate(values_to_translate):
            # Ensure value is treated as string and handle paragraphs properly
            str_value = str(value).replace('\n', ' <br> ').replace('\r', '')

            # Translate the value
            translated_value = translate_text(str_value, translator)

            # Restore line breaks
            translated_value = translated_value.replace(' <br> ', '\n')

            translated_values.append(translated_value)

            # Update progress
            if progress_callback:
                # Calculate progress: completed languages + progress in current language
                overall_progress = (idx + (i + 1) / total_values) / len(target_lang_codes)
                progress_callback(overall_progress)

        # Add translated column to dataframe
        result_df[target_lang_name] = translated_values if translated_values else ""

        # Calculate time taken for this language
        lang_time_taken = round(time.time() - lang_start_time, 2)

        # Add to result table
        result_table.append({
            "Language": target_lang_name,
            "Status": "✅ Success",
            "Time": f"{lang_time_taken} sec"
        })

    # Calculate total time
    total_time = round(time.time() - start_time, 2)

    return result_df, result_table, total_time

def show_metadata_translator():
    """Main function to display and run the Metadata Translator interface"""
    st.title("Metadata made multilingual")

    # Create a nice layout with columns
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### Upload your metadata file
        Upload an Excel or CSV file with metadata to translate.
        The first column should contain field names, and the second column should contain values to translate.
        """)

        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["xlsx", "xls", "csv"],
            help="Upload an Excel (.xlsx, .xls) or CSV file"
        )

    with col2:
        st.markdown("### Language Settings")

        # Source language selection
        source_lang = st.selectbox(
            "Source Language",
            list(language_codes.keys()),
            index=list(language_codes.keys()).index("English") if "English" in language_codes else 0
        )

        # Target languages selection
        target_langs = st.multiselect(
            "Target Languages (Select Multiple)",
            options=list(language_codes.keys()),
            default=["Spanish", "French"] if all(lang in language_codes for lang in ["Spanish", "French"]) else None
        )

    # Process button
    process_button = st.button("Process", type="primary", use_container_width=True)

    if process_button:
        if uploaded_file is not None and target_langs:
            try:
                # Get language codes
                source_lang_code = language_codes[source_lang]
                target_lang_codes = [language_codes[lang] for lang in target_langs]

                # Check if source language is in target languages
                if source_lang_code in target_lang_codes:
                    st.warning(f"⚠️ Source language '{source_lang}' is also selected as a target language. It will be skipped.")

                # Set up progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Define progress callback
                def update_progress(progress):
                    progress_bar.progress(min(progress, 1.0))
                    status_text.text(f"Processing... {int(progress * 100)}% complete")

                # Process the file
                status_text.text("Processing your file...")
                result_df, result_table, total_time = process_metadata_file(
                    uploaded_file,
                    source_lang_code,
                    target_lang_codes,
                    update_progress
                )

                # Complete progress
                progress_bar.progress(1.0)
                status_text.text("Processing complete!")

                # Display results
                st.success(f"✅ Processing complete in {total_time} seconds!")

                # Display results in a table
                st.subheader("Translation Results")
                st.table(result_table)

                # Preview the translated data
                st.subheader("Preview of Translated Data")
                st.dataframe(result_df, use_container_width=True)

                # Prepare file for download
                if uploaded_file.name.endswith('.csv'):
                    # For CSV files
                    output = BytesIO()
                    result_df.to_csv(output, index=False)
                    output.seek(0)
                    mime_type = "text/csv"
                else:
                    # For Excel files
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        result_df.to_excel(writer, index=False, sheet_name='Translated')
                    output.seek(0)
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                # Create download button
                download_filename = f"translated_{uploaded_file.name}"
                st.download_button(
                    label="Download Translated File",
                    data=output,
                    file_name=download_filename,
                    mime=mime_type,
                    key="download-button",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                st.info("Please check your file format and try again.")

        elif not uploaded_file:
            st.error("Please upload a file.")
        elif not target_langs:
            st.error("Please select at least one target language.")

    # Add some helpful information at the bottom
    with st.expander("ℹ️ How to use this tool"):
        st.markdown("""
        ### How to use the Metadata Translator

        1. **Upload your file**: Upload an Excel (.xlsx, .xls) or CSV file containing your metadata.
        2. **Select languages**: Choose the source language of your data and the target languages for translation.
        3. **Process**: Click the Process button to start the translation.
        4. **Download**: Once processing is complete, download your translated file.

        ### File Format Requirements

        - The first column should contain field names (these won't be translated)
        - The second column should contain the values to be translated
        - Additional columns will be preserved in the output file

        ### Notes

        - Translation is performed using Google Translate
        - Large files may take longer to process
        - If the source language is also selected as a target language, it will be skipped
        """)
