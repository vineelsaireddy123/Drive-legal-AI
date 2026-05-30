import json
import re
import os

transcript_path = r'C:\Users\HP\.gemini\antigravity-ide\brain\31ca2e53-5672-44e0-b9bb-9457cc79fe9d\.system_generated\logs\transcript.jsonl'
files_to_restore = [
    'app.py',
    'challan_calculator.py',
    'nlp_engine.py',
    'static/app.js',
    'static/styles.css',
    'static/index.html'
]

file_contents = {}

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            entry = json.loads(line)
            if entry.get('type') == 'TOOL_RESPONSE' and entry.get('status') == 'DONE':
                content_str = entry.get('content', '')
                # Looking for view_file outputs
                if 'File Path: `file:///' in content_str:
                    for filename in files_to_restore:
                        # Convert to standard path format matching the log
                        match_path = filename.replace('/', '\\') if '\\' in filename else filename
                        if match_path in content_str and 'Showing lines 1 to ' in content_str:
                            # Extract the code block starting with line numbers
                            lines = content_str.split('\n')
                            code_lines = []
                            is_code = False
                            for l in lines:
                                if l.startswith('1: '):
                                    is_code = True
                                if is_code:
                                    if l.startswith('The above content shows'):
                                        break
                                    if l.startswith('The above content does NOT show'):
                                        break
                                    # Regex to remove the line number '1: ', '123: ', etc.
                                    clean_line = re.sub(r'^\d+:\s?', '', l)
                                    code_lines.append(clean_line)
                            
                            if code_lines and filename not in file_contents:
                                file_contents[filename] = '\n'.join(code_lines)
                                print(f"Found original content for {filename} ({len(code_lines)} lines)")
        except Exception as e:
            pass

# Write the restored contents back
base_dir = r'c:\Users\HP\Downloads\Project_Intern\hackaton'

for filename, content in file_contents.items():
    filepath = os.path.join(base_dir, filename.replace('/', '\\'))
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Restored {filename}")

# Also restore requirements.txt manually
with open(os.path.join(base_dir, 'requirements.txt'), 'w', encoding='utf-8') as f:
    f.write('flask>=3.0.0\nflask-cors>=4.0.0\n')
print("Restored requirements.txt")

# Delete created files
new_files = ['static\\manifest.json', 'static\\sw.js']
for nf in new_files:
    nf_path = os.path.join(base_dir, nf)
    if os.path.exists(nf_path):
        os.remove(nf_path)
        print(f"Deleted {nf}")
