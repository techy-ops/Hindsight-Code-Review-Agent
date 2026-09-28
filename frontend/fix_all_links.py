import os
import glob
import re
import shutil

base_dir = r"c:\Users\krish\OneDrive\Desktop\Ai-code-review-agent\frontend"
files = glob.glob(os.path.join(base_dir, "**", "*.html"), recursive=True)

href_map = {
    "Pricing": "/pricing/pricing.html",
    "Features": "/",
    "Community": "/",
    "Discord Community": "/",
    "GitHub Repo": "https://github.com",
    "GitHub": "https://github.com",
    "Twitter": "https://twitter.com",
    "Privacy Policy": "/platform_documentation/documentation.html",
    "Privacy": "/platform_documentation/documentation.html",
    "Terms of Service": "/platform_documentation/documentation.html",
    "Terms": "/platform_documentation/documentation.html",
    "Help Center": "/platform_documentation/documentation.html",
    "Support": "/platform_documentation/documentation.html",
    "Status": "/platform_documentation/documentation.html",
    "Security": "/platform_documentation/documentation.html",
    "Integrations": "/platform_documentation/documentation.html",
    "Contact": "/platform_documentation/documentation.html",
    "About": "/platform_documentation/documentation.html",
    "Blog": "/platform_documentation/documentation.html",
    "Careers": "/platform_documentation/documentation.html",
    "Legal": "/platform_documentation/documentation.html",
    "Enterprise": "/pricing/pricing.html",
    "Endpoints": "/api_documentation/api.html",
    "Changelog": "/platform_documentation/documentation.html",
    "Request Schema": "/api_documentation/api.html",
    "Response Schema": "/api_documentation/api.html",
    "Create an account": "/create_account/signup.html",
    "Forgot Password?": "/login/login.html",
    "Settings": "/developer_dashboard/developer.html",
    "Analyzer": "/",
    "Get Started": "/create_account/signup.html"
}

def replace_hrefs(match):
    before_href = match.group(1)
    between_href_and_text = match.group(2)
    text = match.group(3)
    after_text = match.group(4)
    
    text_clean = text.strip()
    clean_text = re.sub(r'<[^>]+>', '', text_clean).strip()
    
    if text_clean in href_map:
        new_href = href_map[text_clean]
        return f'{before_href}href="{new_href}"{between_href_and_text}>{text}{after_text}'
    elif clean_text in href_map:
        new_href = href_map[clean_text]
        return f'{before_href}href="{new_href}"{between_href_and_text}>{text}{after_text}'
        
    # Default fallback
    return f'{before_href}href="/"{between_href_and_text}>{text}{after_text}'

pattern_href = re.compile(r'(<a[^>]*?)href="#"([^>]*?)>(.*?)(</a>)', re.IGNORECASE | re.DOTALL)

def replace_buttons(content):
    content = re.sub(r'<button([^>]+)>(.*?Analyze New Code.*?)</button>', 
                     r'<button\1 onclick="window.location.href=\'/\'">\2</button>', 
                     content, flags=re.DOTALL)
    content = re.sub(r'<button([^>]+)>(.*?Upload Source File.*?)</button>', 
                     r'<button\1 onclick="window.location.href=\'/\'">\2</button>', 
                     content, flags=re.DOTALL)
    content = re.sub(r'<button([^>]+)>(.*?Open Review History.*?)</button>', 
                     r'<button\1 onclick="window.location.href=\'/review_history/history.html\'">\2</button>', 
                     content, flags=re.DOTALL)
    content = re.sub(r'<button([^>]+)>View All</button>', 
                     r'<button\1 onclick="window.location.href=\'/review_history/history.html\'">View All</button>', 
                     content)
    content = re.sub(r'<button([^>]+)>View Review</button>', 
                     r'<button\1 onclick="window.location.href=\'/review_history/history.html\'">View Review</button>', 
                     content)
    return content

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content = pattern_href.sub(replace_hrefs, content)
    new_content = replace_buttons(new_content)
    
    # Fix the brand logos to be clickable back to home
    new_content = re.sub(r'<div class="flex items-center gap-3">\s*<div class="size-8 bg-primary([^"]*)">\s*<span class="material-symbols-outlined text-white">auto_awesome</span>\s*</div>\s*<h2 class="text-xl font-bold tracking-tight">CodeReview <span class="text-primary">AI</span></h2>\s*</div>',
                         r'<div class="flex items-center gap-3 cursor-pointer" onclick="window.location.href=\'/\'">\n                <div class="size-8 bg-primary\1">\n                    <span class="material-symbols-outlined text-white">auto_awesome</span>\n                </div>\n                <h2 class="text-xl font-bold tracking-tight">CodeReview <span class="text-primary">AI</span></h2>\n            </div>', new_content, flags=re.IGNORECASE)

    new_content = re.sub(r'<div class="flex items-center gap-3 text-primary([^>]*)">\s*<span class="material-symbols-outlined text-([^>]*)>terminal</span>\s*<h2 class="text-slate-900([^>]*)>CodeMind AI</h2>\s*</div>',
                         r'<div class="flex items-center gap-3 text-primary cursor-pointer" onclick="window.location.href=\'/\'">\n<span class="material-symbols-outlined text-\2>terminal</span>\n<h2 class="text-slate-900\3>CodeMind AI</h2>\n</div>', new_content, flags=re.IGNORECASE)
                         
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated links in {os.path.basename(file)}")

print("Creating Pricing Page")
pricing_dir = os.path.join(base_dir, "pricing")
os.makedirs(pricing_dir, exist_ok=True)

# Just copy index layout and inject pricing html inside
shutil.copyfile(os.path.join(base_dir, "index.html"), os.path.join(pricing_dir, "pricing.html"))
