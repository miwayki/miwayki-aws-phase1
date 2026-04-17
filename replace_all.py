import os

files_to_check = []
for root, dirs, files in os.walk('bridge'):
    for file in files:
        if file.endswith('.py') or file.endswith('.bak-v010'):
            files_to_check.append(os.path.join(root, file))

for root, dirs, files in os.walk('compose'):
    for file in files:
        if file.endswith('.md') or file.startswith('.env'):
            files_to_check.append(os.path.join(root, file))

for file_path in files_to_check:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'Dify' in content or 'dify' in content or 'DIFY' in content:
            content = content.replace('Dify', 'Langflow')
            content = content.replace('dify', 'langflow')
            content = content.replace('DIFY', 'LANGFLOW')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {file_path}")
    except Exception as e:
        print(f"Error on {file_path}: {e}")

# Rename files if they contain dify
for file_path in files_to_check:
    path_parts = list(os.path.split(file_path))
    if 'dify' in path_parts[-1]:
        path_parts[-1] = path_parts[-1].replace('dify', 'langflow')
        new_path = os.path.join(*path_parts)
        os.rename(file_path, new_path)
        print(f"Renamed {file_path} to {new_path}")
