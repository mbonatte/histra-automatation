import xml.etree.ElementTree as ET

def read_xml(file_path):
    with open(file_path, "r", encoding="utf-16", errors="ignore") as f:
        return ET.fromstring(f.read())

def save_xml(root, path):
    ET.ElementTree(root).write(path, encoding="utf-16", xml_declaration=True)

def mutate_file(in_path, mutator=None, out_path=None):
    root = read_xml(in_path)
    if mutator:
        mutator(root)  # mutate in place
    save_xml(root, out_path or in_path)