import xml.etree.ElementTree as ET
from deep_translator import GoogleTranslator as Translator
from io import BytesIO
import streamlit as st

def translate_text_preserving_tags(element, translator, source_lang='auto', target_lang='en'):
    for subelement in element:
        try:
            if subelement.text:
                translation = translator.translate(subelement.text)
                subelement.text = translation
            if subelement.tail:
                translation = translator.translate(subelement.tail)
                subelement.tail = translation
        except:
            pass
        # Recursively process subelements
        translate_text_preserving_tags(subelement, translator, source_lang=source_lang, target_lang=target_lang)
        # If the subelement has children, translate them too
        if len(subelement) > 0:
            translate_text_preserving_tags(subelement, translator, source_lang=source_lang, target_lang=target_lang)


def translate_xliff(input_file, output_file, source_lang='auto', target_lang='en'):
    ET.register_namespace('', 'urn:oasis:names:tc:xliff:document:1.2')
    tree = ET.parse(input_file)
    root = tree.getroot()
    translator = Translator(source='auto', target=target_lang)

    for trans_unit in root.findall(".//{urn:oasis:names:tc:xliff:document:1.2}trans-unit"):
        source = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}source')
        target = trans_unit.find('{urn:oasis:names:tc:xliff:document:1.2}target')
        if source is not None:
            if target is None:
                target = ET.Element('target')
                trans_unit.append(target)
            else:
                target.clear()
            translate_text_preserving_tags(source, translator, source_lang=source_lang, target_lang=target_lang)
            # Append translated subelements to target
            for subelement in list(source):
                target.append(subelement)


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
