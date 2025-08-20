# guicommands.py
import os
import subprocess

def opensoundsfolder():
    folder_path = os.path.join(os.environ['USERPROFILE'], 'KeyCl')
    os.makedirs(folder_path, exist_ok=True)
    # Open folder (not selecting a file)
    subprocess.Popen(f'explorer "{folder_path}"')