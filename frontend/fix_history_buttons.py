import re
import os
import glob

base_dir = r"c:\Users\krish\OneDrive\Desktop\Ai-code-review-agent\frontend"
files = glob.glob(os.path.join(base_dir, "**", "*.html"), recursive=True)

def fix_history_buttons(content):
    # Fix New Review Button in History page
    content = re.sub(r'<button class="flex items-center gap-2 bg-primary/90 hover:bg-primary text-white px-5 py-2.5 rounded-xl font-bold shadow-lg shadow-primary/20 transition-all">', 
                     r'<button onclick="window.location.href=\'/\'" class="flex items-center gap-2 bg-primary/90 hover:bg-primary text-white px-5 py-2.5 rounded-xl font-bold shadow-lg shadow-primary/20 transition-all">', 
                     content)

    # Fix User Profile Avatars across all pages (already partially fixed index, this fixes the rest)
    content = re.sub(r'<div class="size-10 rounded-full border-2 border-primary bg-primary/20 flex items-center justify-center overflow-hidden">',
                     r'<div class="size-10 rounded-full border-2 border-primary bg-primary/20 flex items-center justify-center overflow-hidden cursor-pointer" onclick="window.location.href=\'/login/login.html\'">',
                     content)

    # Fix Search Bar Input (make it look like it submits)
    content = re.sub(r'<input\s+class="bg-transparent border-none text-sm focus:ring-0 placeholder-slate-500 w-64"\s+placeholder="Search code reviews\.\.\."\s+type="text"\s*/>',
                     r'<input class="bg-transparent border-none text-sm focus:ring-0 placeholder-slate-500 w-64" placeholder="Search code reviews..." type="text" onkeypress="if(event.key === \'Enter\') alert(\'Search functionality coming soon!\')" />',
                     content)
    content = re.sub(r'<input\s+class="bg-transparent border-none focus:ring-0 text-sm placeholder:text-slate-500 w-full"\s+placeholder="Search code reviews\.\.\."\s+type="text"\s*/>',
                     r'<input class="bg-transparent border-none focus:ring-0 text-sm placeholder:text-slate-500 w-full" placeholder="Search code reviews..." type="text" onkeypress="if(event.key === \'Enter\') alert(\'Search functionality coming soon!\')" />',
                     content)
    content = re.sub(r'<input class="bg-transparent border-none focus:ring-0 text-sm placeholder:text-slate-500 w-48" placeholder="Search code reviews\.\.\." type="text"/>',
                     r'<input class="bg-transparent border-none focus:ring-0 text-sm placeholder:text-slate-500 w-48" placeholder="Search code reviews..." type="text" onkeypress="if(event.key === \'Enter\') alert(\'Search functionality coming soon!\')" />',
                     content)

    return content

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content = fix_history_buttons(content)
    
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated buttons in {os.path.basename(file)}")
