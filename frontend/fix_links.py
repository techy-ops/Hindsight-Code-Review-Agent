import os
import glob
import re

base_dir = r"c:\Users\krish\OneDrive\Desktop\Ai-code-review-agent\frontend"
files = glob.glob(os.path.join(base_dir, "**", "*.html"), recursive=True)

link_map = {
    "Dashboard": "/developer_dashboard/developer.html",
    "History": "/review_history/history.html",
    "Docs": "/platform_documentation/documentation.html",
    "Documentation": "/platform_documentation/documentation.html",
    "API": "/api_documentation/api.html",
    "API Docs": "/api_documentation/api.html",
    "Login": "/login/login.html",
    "Sign Up": "/create_account/signup.html"
}

def replace_links(match):
    before_href = match.group(1)
    between_href_and_text = match.group(2)
    text = match.group(3)
    after_text = match.group(4)
    
    text_clean = text.strip()
    if text_clean in link_map:
        new_href = link_map[text_clean]
        return f'{before_href}href="{new_href}"{between_href_and_text}>{text}{after_text}'
    return match.group(0)

# Pattern: <a ... href="#" ... >Text</a>
# We only want to target href="#"
pattern = re.compile(r'(<a[^>]*?)href="#"([^>]*?)>([^<]+)(</a>)', re.IGNORECASE)

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content = pattern.sub(replace_links, content)
    
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated links in {os.path.basename(file)}")
