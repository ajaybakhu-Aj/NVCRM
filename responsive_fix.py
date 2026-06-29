import os
import re

template_dir = r"c:\Users\bakhu\Desktop\CRMERP\templates"

replacements = {
    # Generic missing md:/sm: prefixes for common grids
    r'class="([^"]*)grid grid-cols-2([^"]*)"': r'class="\1grid grid-cols-1 md:grid-cols-2\2"',
    r'class="([^"]*)grid grid-cols-4([^"]*)"': r'class="\1grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4\2"',
    # Common headers that should stack on mobile
    r'class="([^"]*)flex justify-between items-end mb-([^"]*)"': r'class="\1flex flex-col md:flex-row md:justify-between items-start md:items-end gap-4 mb-\2"',
    r'class="([^"]*)flex justify-between items-center mb-([^"]*)"': r'class="\1flex flex-col md:flex-row md:justify-between items-start md:items-center gap-4 mb-\2"',
}

# files where we want to avoid replacing certain grids or need special care
skip_files = ['base.html']

for filename in os.listdir(template_dir):
    if filename in skip_files or not filename.endswith('.html'):
        continue
        
    filepath = os.path.join(template_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    for pattern, replacement in replacements.items():
        # Avoid replacing if already replaced or has responsive classes like md:grid-cols-
        # We can just apply it carefully using regex.
        # But wait, if it already has `md:grid-cols-2` in the class, `grid grid-cols-2` regex will still match if the class is `grid grid-cols-2 md:grid-cols-3`.
        # Let's refine the regex to only match when there is no responsive prefix for it.
        pass

    # Simple replacements that are safer:
    content = content.replace('class="grid grid-cols-2 gap-', 'class="grid grid-cols-1 md:grid-cols-2 gap-')
    content = content.replace('class="grid grid-cols-4 gap-4 mb-8"', 'class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"')
    
    # Header flex replacements (being careful)
    content = content.replace('class="flex justify-between items-end mb-6"', 'class="flex flex-col md:flex-row md:justify-between items-start md:items-end gap-4 mb-6"')
    content = content.replace('class="flex justify-between items-end mb-8"', 'class="flex flex-col md:flex-row md:justify-between items-start md:items-end gap-4 mb-8"')

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filename}")
