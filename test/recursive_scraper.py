# dialogue_parser.py

from bs4 import BeautifulSoup
import json

def parse_dialogue_element(element):
    """
    Recursively parses a BeautifulSoup element to extract dialogue,
    choices, and conditions, maintaining the nested structure.

    Args:
        element: A BeautifulSoup tag/element to process.

    Returns:
        A list of structured data (dictionaries) representing the dialogue.
    """
    dialogue_tree = []

    # Use find_all(recursive=False) for a stable list of direct child tags.
    for child in element.find_all(recursive=False):

        if child.name == 'dl':
            dialogue_tree.extend(parse_dialogue_element(child))

        elif child.name == 'dt':
            dialogue_tree.append({
                'type': 'condition',
                'text': child.get_text(strip=True)
            })

        elif child.name == 'dd':
            speaker_tag = child.find('b', recursive=False)

            # This is a line of spoken dialogue
            if speaker_tag:
                speaker = speaker_tag.get_text(strip=True).replace(':', '')
                line_parts = []
                for sibling in speaker_tag.next_siblings:
                    if getattr(sibling, 'name', None) == 'dl':
                        break
                    line_parts.append(sibling.get_text() if hasattr(sibling, 'get_text') else str(sibling))
                
                line = "".join(line_parts).strip()
                
                entry = {
                    'type': 'dialogue',
                    'speaker': speaker,
                    'line': line
                }
                
                nested_dl = child.find('dl')
                if nested_dl:
                    entry['children'] = parse_dialogue_element(nested_dl)
                
                dialogue_tree.append(entry)

            # This is a player choice
            else:
                dd_clone = child.__copy__()
                nested_dl_in_clone = dd_clone.find('dl')
                if nested_dl_in_clone:
                    nested_dl_in_clone.extract()

                # **THE FIX IS HERE:**
                # Use stripped_strings to get all text parts, then join them with a space.
                # This correctly handles text separated by other tags, like <a>.
                choice_text = " ".join(dd_clone.stripped_strings)

                entry = {
                    'type': 'choice',
                    'text': choice_text
                }
                
                nested_dl = child.find('dl')
                if nested_dl:
                    entry['children'] = parse_dialogue_element(nested_dl)
                
                dialogue_tree.append(entry)
                
    return dialogue_tree


def extract_all_dialogues(html_content):
    """
    Main function to find ALL dialogue containers and initiate the parsing process.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    dialogue_containers = soup.find_all('div', class_='dialogue')
    
    if not dialogue_containers:
        print("Could not find any <div class='dialogue'> containers.")
        return []

    print(f"Found {len(dialogue_containers)} dialogue container(s). Starting recursive parse...")
    
    all_dialogue = []
    for container in dialogue_containers:
        all_dialogue.extend(parse_dialogue_element(container))
        
    return all_dialogue


if __name__ == "__main__":
    source_file = 'dialog_source.html'
    output_file = 'dialogue_final_output.json'

    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            html = f.read()

        extracted_data = extract_all_dialogues(html)

        if extracted_data:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)

            print(f"\nSuccessfully parsed and saved the final dialogue structure to {output_file}")
            print(f"Total top-level entries extracted from all containers: {len(extracted_data)}")

        else:
            print("Could not extract any structured dialogue from the file.")

    except FileNotFoundError:
        print(f"Error: The file '{source_file}' was not found. Please place it in the same directory.")