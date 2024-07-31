import xml.etree.ElementTree as ET
from translate import Translator
from xml.etree.ElementTree import tostring, fromstring
import tempfile
from io import BytesIO

import streamlit as st


def translate_text_preserving_tags(element, translator):
    for subelement in element:
        if subelement.text:
            subelement.text = translator.translate(subelement.text)
        if subelement.tail:
            subelement.tail = translator.translate(subelement.tail)
        translate_text_preserving_tags(subelement, translator)

def translate_xliff(input_file, output_file, source_lang='en', target_lang='pt'):
    ET.register_namespace('', 'urn:oasis:names:tc:xliff:document:1.2')

    # Load and parse the XLIFF file
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Define the translator
    translator = Translator(from_lang=source_lang, to_lang=target_lang)

    # Iterate through each trans-unit element and translate its text
    for trans_unit in root.findall(".//{urn:oasis:names:tc:xliff:document:1.2}trans-unit"):
        source = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}source')
        if source is not None:
            # Clone the source element to create the target element
            target = ET.Element('target')
            for subelement in source:
                target.append(subelement)
            
            # Translate text within the target element
            translate_text_preserving_tags(target, translator)
            
            # Insert the target element right after the source element
            source_index = list(trans_unit).index(source)
            trans_unit.insert(source_index + 1, target)
    
    # Write the modified XML to a new file
    tree.write(output_file, encoding='utf-8', xml_declaration=True)

st.title("XLIFF Translator")

col1, col2 = st.columns([2,1])
container1 = col1.container(height=200)
container2 = col2.container(height=200)
language_codes = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "Arabic": "ar",
    "Portuguese": "pt"
}
source_lang = container2.selectbox("Source Language", list(language_codes.keys()))
target_lang = container2.selectbox("Target Language", list(language_codes.keys()))

uploaded_file = container1.file_uploader("Upload the XLIFF file you wish to convert", type=["xlf"])

if st.button("Translate"):
    if uploaded_file is not None:
        input_file_name = uploaded_file.name
        input_file = BytesIO(uploaded_file.read())
        output_file = BytesIO()
        source_lang = language_codes[source_lang]
        target_lang = language_codes[target_lang]
        with st.spinner('The conversion process has started.. please wait for a few seconds!'):
            if source_lang == target_lang:
                st.write("**Warning:** Source and target language are selected as same!")
            translate_xliff(input_file, output_file, source_lang, target_lang)
        st.success("Translation complete! You can download the file now.", icon="✅")
        st.download_button(
            label="Download Translated XLIFF",
            data=output_file.getvalue(),
            file_name=f"{target_lang}_{input_file_name}",
            mime="application/octet-stream"
        )
    else:
        st.error("Please upload an XLIFF file.")
