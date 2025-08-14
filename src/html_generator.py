# html_generator.py

import os
import re

def sanitize_filename(name):
    """Removes invalid characters from a string to make it a valid filename."""
    name = name.replace(' ', '_')
    return re.sub(r'[\\/*?:"<>|\']', "", name)

def _render_dialogue_nodes(nodes, audio_folder):
    """
    Recursively renders a list of dialogue nodes into HTML.
    """
    if not nodes:
        return ""

    html = '<div class="dialogue-content-block">\n'
    for node in nodes:
        node_type = node.get('type')

        if node_type == 'heading':
            html += f"<h3>{node.get('text', '')}</h3>"

        elif node_type == 'section_header':
            html += f'<h4 class="section-header">{node.get("text", "")}</h4>'
        
        elif node_type == 'cutscene':
            html += '<div class="cutscene-block">'
            if 'children' in node and node['children']:
                html += _render_dialogue_nodes(node['children'], audio_folder)
            html += '</div>'
        
        elif node_type == 'tutorial_block':
            html_content = node.get('html_content', '')
            html += f'<div class="tutorial-container">{html_content}</div>'
        
        elif node_type == 'mission_description':
            title = node.get('title', '')
            content = node.get('content', '')
            html += f'<div class="mission-description-box"><div class="mission-description-title">{title}</div><div class="mission-description-content">{content}</div></div>'

        elif node_type == 'note':
            text = node.get("text", "")
            if text:
                html += f'<div class="note-block"><p>{node.get("text", "")}</p></div>'
            if 'children' in node and node['children']:
                html += _render_dialogue_nodes(node['children'], audio_folder)
            
        elif node_type == 'condition':
            html += f'<p class="condition-item">{node.get("text", "")}</p>'

        elif node_type == 'dialogue':
            is_unavailable = node.get('is_unavailable', False)
            li_class = 'li-dialogue-unavailable' if is_unavailable else ''
            
            html += f"<ul class='node-list'><li class='li-dialogue {li_class}'>"
            speaker = node.get('speaker', 'Unknown')
            line = node.get('line', '')
            audio_filename = node.get('audio_filename')
            
            html += f'<div class="dialogue-item">'
            html += '<div class="audio-cell">'
            if audio_filename:
                audio_id = os.path.join(audio_folder, audio_filename).replace('\\', '/')
                html += f'<button class="play-button" data-audio-id="{audio_id}">▶</button>'
                html += f'<audio id="{audio_id}" src="{audio_id}" preload="metadata"></audio>'
            html += '</div>'
            html += f'<div class="text-cell"><b class="speaker">{speaker}:</b> {line}</div>'
            html += '</div>'
            
            if 'children' in node and node['children']:
                html += _render_dialogue_nodes(node['children'], audio_folder)
            
            html += "</li></ul>\n"

        elif node_type == 'choice':
            html += f"<ul class='node-list'><li class='li-choice'>"
            text = node.get('text', '')
            html += f'<div><i>&rarr; {text}</i></div>'
            if 'children' in node and node['children']:
                html += _render_dialogue_nodes(node['children'], audio_folder)
            html += "</li></ul>"

    html += "</div>\n"
    return html

def generate_mission_html(content_items, page_title, audio_folder, mission_hierarchy, current_mission_url):
    """
    Generates the final HTML page with a new visual design and persistent theme switcher.
    """
    mission_nav_html = """
    <nav class='mission-nav'>
        <div class='nav-header'>
            <h2>All Missions</h2>
        </div>
        <div class='nav-scroll-area'>
            <ul>"""
    for chap_idx, chapter in enumerate(mission_hierarchy):
        is_in_chapter = any(mission['url'] == current_mission_url for sc in chapter['sub_chapters'] for mission in sc['missions'])
        chap_collapsed_class = '' if is_in_chapter else 'collapsed'
        
        mission_nav_html += f"<li><span class='nav-title {chap_collapsed_class}' data-target='chapter-{chap_idx}'>{chapter['chapter']}</span>"
        mission_nav_html += f"<ul id='chapter-{chap_idx}' class='mission-list {chap_collapsed_class}'>"
        
        for sub_chap_idx, sub_chapter in enumerate(chapter['sub_chapters']):
            is_in_sub_chapter = any(mission['url'] == current_mission_url for mission in sub_chapter['missions'])
            sub_chap_collapsed_class = '' if is_in_sub_chapter else 'collapsed'
            
            mission_nav_html += f"<li><span class='nav-title {sub_chap_collapsed_class}' data-target='sub-chapter-{chap_idx}-{sub_chap_idx}'>{sub_chapter['title']}</span>"
            mission_nav_html += f"<ul id='sub-chapter-{chap_idx}-{sub_chap_idx}' class='mission-list {sub_chap_collapsed_class}'>"
            
            for mission in sub_chapter['missions']:
                is_current = 'class="current-mission"' if mission['url'] == current_mission_url else ''
                safe_name = sanitize_filename(mission['full_title'])
                local_url = f"{safe_name}.html"
                mission_nav_html += f"<li><a href='{local_url}' {is_current}>{mission['title']}</a></li>"
            
            mission_nav_html += "</ul></li>"
        mission_nav_html += "</ul></li>"
    mission_nav_html += """
            </ul>
        </div>
        <div class='nav-footer'>
            <button class='theme-toggle' aria-label='Toggle Theme'>
                <span class='theme-icon-light'>☀️</span>
                <span class='theme-icon-dark'>◑</span>
            </button>
        </div>
    </nav>"""

    main_content_html = _render_dialogue_nodes(content_items, audio_folder)
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title} - Dialogue Archive</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
    
    <style>
    :root {{
        --nav-width: 320px;
        /* Light Theme Vars */
        --accent-color-light: #007bff;
        --text-primary-light: #212529;
        --text-secondary-light: #353a3f;
        --bg-main-light: #ffffff;
        --bg-nav-light: #f8f9fa;
        --border-color-light: #dee2e6;
        --note-bg-light: #f1f3f5;
        --speaker-color-light: #0056b3;
        --choice-color-light: #0b7285;
        --unavailable-color-light: #dc3545;
        --cutscene-text-light: #343a40;
        --cutscene-bg-light: #f8f9fa;
        --info-bg-light: #f8f9fa;
        --info-text-light: #495057;
        /* Dark Theme Vars */
        --accent-color-dark: #00aaff;
        --text-primary-dark: #e0e0e0;
        --text-secondary-dark: #888888;
        --bg-main-dark: #121212;
        --bg-nav-dark: #1e1e1e;
        --border-color-dark: #333333;
        --note-bg-dark: #222222;
        --speaker-color-dark: #80dfff;
        --choice-color-dark: #22b8cf;
        --unavailable-color-dark: #e57373;
        --cutscene-text-dark: #ced4da;
        --cutscene-bg-dark: #1c1c1c;
        --info-bg-dark: #2c2c2c;
        --info-text-dark: #adb5bd;
    }}
    body {{
        --accent-color: var(--accent-color-light);
        --text-primary: var(--text-primary-light);
        --text-secondary: var(--text-secondary-light);
        --bg-main: var(--bg-main-light);
        --bg-nav: var(--bg-nav-light);
        --border-color: var(--border-color-light);
        --note-bg: var(--note-bg-light);
        --speaker-color: var(--speaker-color-light);
        --choice-color: var(--choice-color-light);
        --unavailable-color: var(--unavailable-color-light);
        --cutscene-text: var(--cutscene-text-light);
        --cutscene-bg: var(--cutscene-bg-light);
        --info-bg: var(--info-bg-light);
        --info-text: var(--info-text-light);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: var(--bg-main);
        color: var(--text-primary);
        transition: background-color 0.2s, color 0.2s;
        margin: 0;
        padding: 0;
        height: 100vh;
        overflow: hidden;
    }}
    body.dark-theme {{
        --accent-color: var(--accent-color-dark);
        --text-primary: var(--text-primary-dark);
        --text-secondary: var(--text-secondary-dark);
        --bg-main: var(--bg-main-dark);
        --bg-nav: var(--bg-nav-dark);
        --border-color: var(--border-color-dark);
        --note-bg: var(--note-bg-dark);
        --speaker-color: var(--speaker-color-dark);
        --choice-color: var(--choice-color-dark);
        --unavailable-color: var(--unavailable-color-dark);
        --cutscene-text: var(--cutscene-text-dark);
        --cutscene-bg: var(--cutscene-bg-dark);
        --info-bg: var(--info-bg-dark);
        --info-text: var(--info-text-dark);
    }}

    .nav-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 999; opacity: 0; visibility: hidden; transition: opacity 0.3s ease; }}
    body.nav-open .nav-overlay {{ opacity: 1; visibility: visible; }}
    .mission-nav {{ width: var(--nav-width); height: 100vh; position: fixed; top: 0; left: 0; background-color: var(--bg-nav); border-right: 1px solid var(--border-color); z-index: 1000; transform: translateX(-100%); transition: transform 0.3s ease, background-color 0.2s; display: flex; flex-direction: column; }}
    body.nav-open .mission-nav {{ transform: translateX(0); box-shadow: 3px 0 15px rgba(0,0,0,0.1); }}
    .nav-header {{ padding: 0 1.5em; flex-shrink: 0; }}
    .nav-scroll-area {{ flex-grow: 1; overflow-y: auto; padding: 0 1.5em; }}
    .nav-footer {{ padding: 1em 1.5em; flex-shrink: 0; border-top: 1px solid var(--border-color); }}
    .page-header {{ display: flex; align-items: center; padding: 0.5em 1em; background-color: var(--bg-nav); border-bottom: 1px solid var(--border-color); position: sticky; top: 0; z-index: 500; }}
    .nav-toggle {{ background: none; border: none; font-size: 1.5rem; cursor: pointer; padding: 0.2em 0.5em; color: var(--text-primary); }}
    
    /* --- MODIFIED: Mobile-specific layout adjustments --- */
    /* By default, main-wrapper is the primary scroll container */
    .main-wrapper {{
        flex-grow: 1;
        overflow-y: auto;
        height: 100vh; /* Ensure it takes up full height to allow scrolling */
        -webkit-overflow-scrolling: touch; /* Smoother scrolling on iOS */
    }}

    @media (min-width: 900px) {{
        .page-header {{ display: none; }}
        body {{ display: flex; }}
        .mission-nav {{ transform: translateX(0); position: relative; }}
        /* --- MODIFIED: On desktop, the main-wrapper no longer needs a fixed height, as it is part of a flex container --- */
        .main-wrapper {{ height: auto; }}
        main.container {{ margin: 0 auto; }}
    }}

    .theme-toggle {{ width: 100%; background-color: var(--note-bg); border: 1px solid var(--border-color); color: var(--text-primary); padding: 0.6em; border-radius: 8px; cursor: pointer; font-size: 1rem; text-align: center; }}
    .theme-toggle .theme-icon-dark {{ display: none; }}
    .theme-toggle .theme-icon-light {{ display: inline; }}
    body.dark-theme .theme-toggle .theme-icon-dark {{ display: inline; }}
    body.dark-theme .theme-toggle .theme-icon-light {{ display: none; }}

    .mission-nav h2 {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem; }}
    .mission-nav ul {{ list-style: none; padding: 0; margin: 0; }}
    .mission-nav .nav-title {{ font-weight: 500; cursor: pointer; user-select: none; display: flex; align-items: center; padding: 0.6em 0; }}
    .mission-nav .nav-title::before {{ content: '▶'; font-size: 0.6em; margin-right: 0.6em; transition: transform 0.2s; }}
    .mission-nav .nav-title:not(.collapsed)::before {{ transform: rotate(90deg); }}
    .mission-nav .mission-list {{ padding-left: 1em; border-left: 1px solid var(--border-color); max-height: 2000px; overflow: hidden; transition: max-height 0.3s ease-in-out; }}
    .mission-nav .mission-list.collapsed {{ max-height: 0; }}
    .mission-nav a {{ display: block; padding: 0.5em 0.8em; color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; border-radius: 6px;}}
    .mission-nav a:hover {{ background-color: var(--note-bg); color: var(--text-primary); }}
    .mission-nav a.current-mission {{ font-weight: 600; color: var(--accent-color); }}

    main.container {{ padding: 2em; flex-grow: 1; max-width: 800px; }}
    h1 {{ font-weight: 700; font-size: 2rem; margin-top: 0; }}
    h3 {{ font-size: 1.25rem; font-weight: 600; text-align: center; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary); margin: 4em 0 2em 0; border-bottom: 1px solid var(--border-color); padding-bottom: 0.6em; }}
    
    .section-header {{ text-align: center; font-weight: 500; font-size: 0.9rem; color: var(--text-secondary); margin: 2.5em 0 1em 0; display: flex; align-items: center; }}
    .section-header::before, .section-header::after {{ content: ''; flex-grow: 1; border-bottom: 1px solid var(--border-color); }}
    .section-header::before {{ margin-right: 0.8em; }}
    .section-header::after {{ margin-left: 0.8em; }}
    
    .mission-description-box {{ background-color: var(--bg-nav); border: 1px solid var(--border-color); border-radius: 8px; margin: 2em 0; }}
    .mission-description-title {{ font-weight: 600; padding: 0.8em 1.2em; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; }}
    .mission-description-title::before {{ content: ''; display: inline-block; width: 20px; height: 20px; margin-right: 0.7em; background-image: url('https://static.wikia.nocookie.net/houkai-star-rail/images/9/93/UI_Trailblaze_Mission.png'); background-size: contain; background-repeat: no-repeat; }}
    .mission-description-content {{ padding: 1.2em; color: var(--text-secondary); line-height: 1.7; white-space: pre-line; }}
    
    .condition-item {{ text-align: center; color: var(--text-secondary); margin: 0.1em 0; font-size: 0.85rem; white-space: pre-line; }}

    .dialogue-content-block ul.node-list {{ list-style-type: none; padding: 0; margin: 1em 0; }}
    .li-dialogue {{ padding-left: 1em; border-left: 2px solid var(--border-color); list-style-type: none;}}
    .dialogue-item {{ display: flex; align-items: flex-start; margin: 0.75em 0; }}
    .speaker {{ color: var(--speaker-color); font-weight: 600; }}
    .audio-cell {{ flex-shrink: 0; width: 40px; padding-top: 2px; }}
    .play-button {{ background: transparent; border: 1px solid var(--border-color); color: var(--text-secondary); cursor: pointer; width: 28px; height: 28px; border-radius: 50%; }}
    .li-choice {{ margin: 0.5em 0 0.5em 3.5em; color: var(--choice-color); list-style-type: none;}}
    .li-dialogue-unavailable .dialogue-item {{ color: var(--unavailable-color); text-decoration: line-through; opacity: 0.8; }}
    .li-dialogue-unavailable .speaker {{ color: var(--unavailable-color); }}
    .li-dialogue-unavailable::before {{ content: '❌'; margin-left: -2.3em; margin-right: 1em; float: left; text-decoration: none; opacity: 0.8; }}

    .cutscene-block {{ margin: 2em auto; padding: 0em 0em; background-color: var(--cutscene-bg); border: 1px solid var(--border-color); border-radius: 8px; max-width: 85%; font-family: 'Lora', serif; }}
    .cutscene-block .node-list {{ margin: 0; }}
    .cutscene-block .li-dialogue {{ border: none; padding: 0; margin-bottom: 0.85em; text-align: center; list-style-type: none; line-height: 1.6; }}
    .cutscene-block .li-dialogue:last-child {{ margin-bottom: 0; }}
    .cutscene-block .dialogue-item {{ display: inline; justify-content: center; }}
    .cutscene-block .text-cell {{ color: var(--cutscene-text); }}
    .cutscene-block .speaker {{ color: var(--text-secondary); font-weight: 500; font-style: italic; font-size: 1em; }}
    .cutscene-block .audio-cell {{ display: none; }}

    .note-block,
    .tutorial-container dt,
    .tutorial-container dd dd {{
        margin: 0.3em auto;
        padding: 0.1em 0em;
        background-color: var(--info-bg);
        border-radius: 4px;
        max-width: 80%;
        text-align: center;
        font-size: 0.9rem;
        color: var(--info-text);
        border: none;
    }}
    body.dark-theme .note-block,
    body.dark-theme .tutorial-container dt,
    body.dark-theme .tutorial-container dd dd {{
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    }}
    .note-block p {{ margin: 0.3em 0em; padding: 0.3em; }}
    .tutorial-container {{ margin: 2em 0; }}
    .tutorial-container dl, .tutorial-container dd {{ margin: 0; padding: 0; border: none; list-style-type: none; }}
    .tutorial-container .text-highlight {{ color: var(--accent-color); font-weight: 500; }}

    </style>
</head>
<body>
    {mission_nav_html}
    <div class="main-wrapper">
        <header class="page-header">
            <button class="nav-toggle" aria-label="Open navigation">☰</button>
        </header>
        <main class="container">
            <h1>{page_title}</h1>
            {main_content_html}
        </main>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const body = document.body;
            const navToggle = document.querySelector('.nav-toggle');
            const navOverlay = document.querySelector('.nav-overlay');
            const themeToggle = document.querySelector('.theme-toggle');

            function openNav() {{ body.classList.add('nav-open'); }}
            function closeNav() {{ body.classList.remove('nav-open'); }}
            if (navToggle) {{ navToggle.addEventListener('click', () => body.classList.contains('nav-open') ? closeNav() : openNav()); }}
            if (navOverlay) {{ navOverlay.addEventListener('click', () => closeNav()); }}
            document.querySelectorAll('.nav-title').forEach(title => {{
                title.addEventListener('click', () => {{
                    title.classList.toggle('collapsed');
                    document.getElementById(title.dataset.target)?.classList.toggle('collapsed');
                }});
            }});

            let currentlyPlaying = null;
            document.querySelectorAll('.play-button').forEach(button => {{
                button.addEventListener('click', () => {{
                    const audio = document.getElementById(button.dataset.audioId);
                    if (!audio) return;
                    if (audio.paused) {{
                        if (currentlyPlaying && currentlyPlaying.audio !== audio) {{
                            currentlyPlaying.audio.pause();
                            currentlyPlaying.button.innerHTML = '▶';
                        }}
                        audio.play();
                        button.innerHTML = '&#9632;';
                        currentlyPlaying = {{ audio, button }};
                    }} else {{
                        audio.pause();
                        audio.currentTime = 0;
                        button.innerHTML = '▶';
                        currentlyPlaying = null;
                    }}
                    audio.onended = () => {{
                        button.innerHTML = '▶';
                        if (currentlyPlaying?.audio === audio) currentlyPlaying = null;
                    }};
                }});
            }});

            function applyTheme(theme) {{
                if (theme === 'dark') body.classList.add('dark-theme');
                else body.classList.remove('dark-theme');
            }}
            
            const savedTheme = localStorage.getItem('theme') || 'light';
            applyTheme(savedTheme);

            if(themeToggle) {{
                themeToggle.addEventListener('click', () => {{
                    const newTheme = body.classList.contains('dark-theme') ? 'light' : 'dark';
                    localStorage.setItem('theme', newTheme);
                    applyTheme(newTheme);
                }});
            }}
        }});
    </script>
</body>
</html>
"""