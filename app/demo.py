import paramiko
import xml.etree.ElementTree as ET
from tqdm import tqdm

# SSH credentials
hostname = '185.116.6.10'
port = 8000
username = 'sunanda'
password = 'test1234'

# Path to the XML file on the remote server
remote_xml_path = '/media/IngressData/ConfluenceXML/entities.xml'

# Function to recursively convert XML to a dictionary
def xml_to_dict(element):
    result = {element.tag: {} if element.attrib else None}
    if element.attrib:
        result[element.tag].update(('@' + k, v) for k, v in element.attrib.items())
    if element.text and element.text.strip():
        result[element.tag] = element.text.strip()
    children = list(element)
    if children:
        result[element.tag] = {}
        for child in children:
            child_dict = xml_to_dict(child)
            for key, val in child_dict.items():
                if key in result[element.tag]:
                    if isinstance(result[element.tag][key], list):
                        result[element.tag][key].append(val)
                    else:
                        result[element.tag][key] = [result[element.tag][key], val]
                else:
                    result[element.tag][key] = val
    return result

# Function to convert dictionary back to XML
from xml.etree.ElementTree import Element, tostring

def dict_to_xml(tag, d):
    elem = Element(tag)
    if isinstance(d, dict):
        for key, val in d.items():
            child = Element(key)
            if isinstance(val, dict):
                child.append(dict_to_xml(key, val))
            else:
                child.text = str(val)
            elem.append(child)
    else:
        elem.text = str(d)
    return elem

# Initialize SSH client
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

sftp = None  # Initialize sftp variable

try:
    # Connect to the remote server
    ssh.connect(hostname, port=port, username=username, password=password)

    # Open an SFTP session
    sftp = ssh.open_sftp()

    # Get the file size for progress tracking
    file_info = sftp.stat(remote_xml_path)
    file_size = file_info.st_size

    # Open the remote file
    with sftp.open(remote_xml_path, 'r') as remote_file:
        # Set up the progress bar
        progress = tqdm(total=file_size, unit='B', unit_scale=True, desc="Downloading XML")
        
        # Read the file in chunks and update the progress bar
        xml_content = ""
        chunk_size = 1024
        while True:
            chunk = remote_file.read(chunk_size)
            if not chunk:
                break
            xml_content += chunk
            progress.update(len(chunk))
        
        progress.close()

    # Parse the XML content
    root = ET.fromstring(xml_content)

    # Convert XML to dictionary
    xml_dict = xml_to_dict(root)

    # Convert the dictionary back to XML
    new_xml_elem = dict_to_xml('Root', xml_dict)  # Assuming 'Root' as the root element tag
    new_xml_tree = ET.ElementTree(new_xml_elem)

    # Save the new XML to a file
    new_xml_tree.write('output.xml', encoding='utf-8', xml_declaration=True)

    print("XML successfully downloaded, converted, and saved to 'output.xml'.")

finally:
    # Safely close the SFTP session and SSH connection
    if sftp:
        sftp.close()
    ssh.close()
