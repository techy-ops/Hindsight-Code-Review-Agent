import os
import glob

base_dir = r"c:\Users\krish\OneDrive\Desktop\Ai-code-review-agent\frontend"
files = glob.glob(os.path.join(base_dir, "**", "*.html"), recursive=True)

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content = content.replace(r"\'/\'", "'/'")
    new_content = new_content.replace(r"\'/review_history/history.html\'", "'/review_history/history.html'")
    
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed quotes in {os.path.basename(file)}")
