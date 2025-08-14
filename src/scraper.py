# scraper.py

import os
import re
import requests
from bs4 import BeautifulSoup

def sanitize_filename(name):
    """Removes invalid characters from a string to make it a valid filename."""
    name = name.replace(' ', '_')
    return re.sub(r'[\\/*?:"<>|\']', "", name)

def scrape_mission_hierarchy(html_content):
    """
    Scrapes the main missions page to get a structured list of all chapters, 
    sub-chapters, and their missions.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    hierarchy = []
    mission_table = soup.find('table', class_='article-table')
    if not mission_table or not mission_table.find('tbody'):
        return []
    
    current_chapter = None
    for row in mission_table.find('tbody').find_all('tr'):
        if th := row.find('th', attrs={'colspan': '3'}):
            if a_tag := th.find('a'):
                chapter_title = a_tag.get_text(strip=True)
                current_chapter = {'chapter': chapter_title, 'sub_chapters': []}
                hierarchy.append(current_chapter)
        
        elif (td_with_b := row.find('td')) and td_with_b.find('b'):
            if current_chapter:
                sub_chapter_title = td_with_b.get_text(strip=True)
                current_sub_chapter = {'title': sub_chapter_title, 'missions': []}
                
                mission_list_cell = td_with_b.find_next_sibling('td')
                if mission_list_cell:
                    for link in mission_list_cell.find_all('a', href=True):
                        if '/wiki/' in link['href'] and 'Category:' not in link['href']:
                            mission_title_text = link.get_text(strip=True)
                            if mission_title_text:
                                current_sub_chapter['missions'].append({
                                    'title': mission_title_text,
                                    'full_title': f"{sub_chapter_title} - {mission_title_text}",
                                    'url': "https://honkai-star-rail.fandom.com" + link['href']
                                })
                
                if current_sub_chapter['missions']:
                    current_chapter['sub_chapters'].append(current_sub_chapter)
                                
    return hierarchy


def _recursive_parse_dialogue(element):
    """
    The core recursive parser for the contents of a <div class="dialogue">.
    """
    dialogue_tree = []
    children = element.find_all(recursive=False)
    i = 0
    while i < len(children):
        child = children[i]

        if child.name == 'dl' and child.find('dt', string='(Interactive tutorial)', recursive=False):
            dialogue_tree.append({'type': 'tutorial_block', 'html_content': str(child)})
            i += 1
            continue
        
        if child.name == 'dl':
            dialogue_tree.extend(_recursive_parse_dialogue(child))
            i += 1
            continue
        
        if child.name == 'dt':
            condition_texts = []
            while i < len(children) and children[i].name == 'dt':
                condition_texts.append(children[i].get_text(strip=True))
                i += 1
            full_condition_text = "\n".join(condition_texts)
            dialogue_tree.append({'type': 'condition', 'text': full_condition_text})
            continue

        if child.name == 'dd':
            description_div = child.find('div', class_='srw-description')
            if description_div:
                title_div = description_div.find('div', class_='srw-description-title')
                content_div = description_div.find('div', class_='srw-description-content')
                if title_div and content_div:
                    for br in content_div.find_all('br'):
                        br.replace_with('\n')
                    dialogue_tree.append({
                        'type': 'mission_description',
                        'title': title_div.get_text(strip=True),
                        'content': content_div.get_text(strip=True)
                    })
                    i += 1
                    continue

            strikethrough_tag = child.find('s')
            parse_target = strikethrough_tag if strikethrough_tag else child
            
            speaker_tag = parse_target.find('b', recursive=False)

            if speaker_tag:
                speaker = speaker_tag.get_text(strip=True).replace(':', '')
                audio_url = None
                if not strikethrough_tag:
                    if audio_tag := child.find('a', class_='internal', href=re.compile(r'\.ogg')):
                        audio_url = audio_tag['href']
                
                clone = parse_target.__copy__()
                if clone.find(class_='audio-button'): clone.find(class_='audio-button').decompose()
                if clone.find('b'): clone.find('b').decompose()
                if clone.find('dl'): clone.find('dl').decompose()
                line = " ".join(clone.stripped_strings)
                
                entry = { 'type': 'dialogue', 'speaker': speaker, 'line': line, 'audio_url': audio_url, 'is_unavailable': bool(strikethrough_tag) }

                if nested_dl := child.find('dl'):
                    entry['children'] = _recursive_parse_dialogue(nested_dl)
                dialogue_tree.append(entry)

            else:
                has_choice_icon = child.find('img', src=re.compile(r'Icon_Dialogue_Arrow|Icon_Dialogue_Talk'))
                has_nested_dialogue = child.find('dl', recursive=False)

                dd_clone = child.__copy__()
                if nested_dl_in_clone := dd_clone.find('dl'):
                    nested_dl_in_clone.extract()
                text_content = " ".join(dd_clone.stripped_strings)

                if has_choice_icon or (has_nested_dialogue and text_content):
                    entry = {'type': 'choice', 'text': text_content}
                elif not text_content and has_nested_dialogue:
                    entry = {'type': 'cutscene', 'text': ''}
                else:
                    entry = {'type': 'note', 'text': text_content}

                if nested_dl := child.find('dl'):
                    entry['children'] = _recursive_parse_dialogue(nested_dl)
                
                if entry.get('text') or entry.get('children'):
                    dialogue_tree.append(entry)
            i += 1
        else:
            i += 1

    return dialogue_tree

def scrape_page_content(html_content):
    """
    Finds the main dialogue heading and processes all following elements.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    dialogue_heading = soup.find('span', id=re.compile(r'Dialogue|Transcript|Story'))
    if not dialogue_heading: return []
    
    start_node = dialogue_heading.find_parent(['h2', 'h3'])
    if not start_node: return []

    content_tree = []
    elements = list(start_node.find_next_siblings())
    i = 0
    while i < len(elements):
        element = elements[i]
        
        if element.name == 'h2': break
        
        if element.name in ['h3', 'h4']:
            element_clone = element.__copy__()
            if edit_section := element_clone.find('span', class_='mw-editsection'):
                edit_section.decompose()
            text = element_clone.get_text(strip=True)
            if element.name == 'h3':
                content_tree.append({'type': 'heading', 'text': text})
            else:
                content_tree.append({'type': 'section_header', 'text': text})
            i += 1
            continue

        # --- NEW: Added top-level check for Mission Description box ---
        if element.name == 'dl':
            description_div = element.find('div', class_='srw-description')
            if description_div:
                title_div = description_div.find('div', class_='srw-description-title')
                content_div = description_div.find('div', class_='srw-description-content')
                if title_div and content_div:
                    for br in content_div.find_all('br'):
                        br.replace_with('\n')
                    content_tree.append({
                        'type': 'mission_description',
                        'title': title_div.get_text(strip=True),
                        'content': content_div.get_text(strip=True)
                    })
                    i += 1
                    continue
        # --- End of modification ---

        if element.name == 'p':
            text = " ".join(element.stripped_strings)
            if text:
                note_item = {'type': 'note', 'text': text}
                if (i + 1) < len(elements):
                    next_element = elements[i+1]
                    if next_element.name == 'div' and 'dialogue' in next_element.get('class', []):
                        dialogue_nodes = _recursive_parse_dialogue(next_element)
                        note_item['children'] = dialogue_nodes
                        i += 1
                content_tree.append(note_item)
            i += 1
            continue
            
        if element.name == 'div' and 'dialogue' in element.get('class', []):
            dialogue_nodes = _recursive_parse_dialogue(element)
            content_tree.extend(dialogue_nodes)
            i += 1
            continue
        
        i += 1
            
    return content_tree

def download_audio_files(content_items, audio_folder):
    """
    Recursively finds all dialogue items with an 'audio_url' and downloads the files.
    """
    os.makedirs(audio_folder, exist_ok=True)
    
    def find_audio_urls(items):
        urls = []
        for item in items:
            if item.get('type') == 'dialogue' and item.get('audio_url'):
                urls.append(item)
            if 'children' in item:
                urls.extend(find_audio_urls(item['children']))
        return urls

    dialogue_with_audio = find_audio_urls(content_items)
    if not dialogue_with_audio: return content_items

    print(f"  -> Found {len(dialogue_with_audio)} audio file(s) to download...")
    for i, item in enumerate(dialogue_with_audio):
        filename = f"audio_{sanitize_filename(item['speaker'])}_{i}.ogg"
        path = os.path.join(audio_folder, filename)
        item['audio_filename'] = filename
        
        if os.path.exists(path): continue
            
        try:
            with requests.get(item['audio_url'], stream=True, timeout=15) as res:
                res.raise_for_status()
                with open(path, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)
        except requests.exceptions.RequestException as e:
            print(f"    -> FAILED to download {item['audio_url']}: {e}")
            item['audio_filename'] = None
            
    return content_items