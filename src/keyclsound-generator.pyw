import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import random
import requests
import pygame

# ----------------------------
# Helper Functions
# ----------------------------

def generate_random_filename():
    return f"{random.randint(10000000, 99999999)}.keyclsound"

BASE_API_URL = "https://api.github.com/repos/OptionallyBlueStudios/KeyCL/contents"
current_path = ""  # Track navigation inside repo


def fetch_repo_contents(path=""):
    """
    Fetch contents of a path in the KeyCL repo.
    """
    api_url = f"{BASE_API_URL}/{path}" if path else BASE_API_URL
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception:
        return []


def save_keyclsound(data):
    filename = generate_random_filename()
    with open(filename, "w", encoding="utf-8") as f:
        f.write(data)
    return filename


# ----------------------------
# UI Setup
# ----------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("KeyCLSound Generator")
root.geometry("700x700")

pygame.mixer.init()

selected_url = tk.StringVar()

# --- Metadata Section ---
meta_frame = ctk.CTkFrame(root)
meta_frame.pack(pady=10, padx=20, fill="x")

ctk.CTkLabel(meta_frame, text="Sound Metadata", font=("Arial", 16, "bold")).pack(pady=5)

title_entry = ctk.CTkEntry(meta_frame, placeholder_text="Title")
title_entry.pack(pady=5, fill="x")

author_entry = ctk.CTkEntry(meta_frame, placeholder_text="Author (Creator/Importer)")
author_entry.pack(pady=5, fill="x")

desc_entry = ctk.CTkEntry(meta_frame, placeholder_text="Description")
desc_entry.pack(pady=5, fill="x")

tags_entry = ctk.CTkEntry(meta_frame, placeholder_text="Tags (comma-separated)")
tags_entry.pack(pady=5, fill="x")

# --- Repo Browser Section ---
repo_frame = ctk.CTkFrame(root)
repo_frame.pack(pady=10, padx=20, fill="both", expand=True)

ctk.CTkLabel(repo_frame, text="GitHub Repo Browser", font=("Arial", 16, "bold")).pack(pady=5)

repo_label = ctk.CTkLabel(repo_frame, text="Browsing: /")
repo_label.pack(pady=2)

files_listbox = tk.Listbox(repo_frame, height=12)
files_listbox.pack(pady=5, fill="both", expand=True, padx=10)

# Manual URL
manual_url_entry = ctk.CTkEntry(repo_frame, placeholder_text="Or enter direct URL to .mp3/.wav/.ogg")
manual_url_entry.pack(pady=5, fill="x", padx=10)

# --- Controls Section ---
control_frame = ctk.CTkFrame(root)
control_frame.pack(pady=10, padx=20, fill="x")


def load_repo(path=""):
    global current_path
    current_path = path
    repo_label.configure(text=f"Browsing: /{path}" if path else "Browsing: /")

    items = fetch_repo_contents(path)
    files_listbox.delete(0, tk.END)

    if path:
        files_listbox.insert(tk.END, "[..]")  # back option

    for item in items:
        if item['type'] == "dir":
            prefix = "📁 "
        elif item['type'] == "file" and item['name'].endswith((".mp3", ".wav", ".ogg")):
            prefix = "🎵 "
        else:
            prefix = "📄 "
        files_listbox.insert(tk.END, prefix + item['name'])

    files_listbox.bind("<<ListboxSelect>>", lambda e: select_item(items))


def select_item(items):
    selection = files_listbox.curselection()
    if not selection:
        return
    idx = selection[0]

    if current_path and idx == 0:
        # Go up one folder
        parent = "/".join(current_path.split("/")[:-1])
        load_repo(parent)
        return

    item = items[idx if not current_path else idx - 1]

    if item['type'] == "dir":
        load_repo(item['path'])
    elif item['type'] == "file":
        if item['name'].endswith((".mp3", ".wav", ".ogg")):
            selected_url.set(item['download_url'])
            manual_url_entry.delete(0, tk.END)
            manual_url_entry.insert(0, selected_url.get())
        else:
            messagebox.showinfo("Info", "Only .mp3, .wav, or .ogg can be selected for KeyCL.")


def generate_file():
    final_url = manual_url_entry.get().strip()

    if not author_entry.get().strip() or not tags_entry.get().strip() or not final_url:
        messagebox.showerror("Error", "Author, Tags, and URL are required!")
        return

    if not final_url.endswith((".mp3", ".wav", ".ogg")):
        messagebox.showerror("Error", "URL must end with .mp3, .wav, or .ogg")
        return

    data = (
        f"title: {title_entry.get().strip() or 'Untitled Song'}\n"
        f"author: {author_entry.get().strip()}\n"
        f"description: {desc_entry.get().strip()}\n"
        f"tags: {tags_entry.get().strip()}\n"
        f"url: {final_url}\n"
    )

    filename = save_keyclsound(data)
    messagebox.showinfo("Success", f"Saved as {filename}")


def preview_sound():
    final_url = manual_url_entry.get().strip()
    if not final_url.endswith((".mp3", ".wav", ".ogg")):
        messagebox.showerror("Error", "Please select a valid sound file to preview.")
        return
    try:
        import tempfile
        r = requests.get(final_url)
        if r.status_code == 200:
            ext = final_url.split(".")[-1]
            tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            tmpfile.write(r.content)
            tmpfile.close()

            pygame.mixer.music.load(tmpfile.name)
            pygame.mixer.music.play()
        else:
            messagebox.showerror("Error", "Failed to download sound.")
    except Exception as e:
        messagebox.showerror("Error", f"Preview failed: {e}")


def stop_preview():
    pygame.mixer.music.stop()


browse_button = ctk.CTkButton(control_frame, text="Load Repo Root", command=lambda: load_repo(""))
browse_button.pack(side="left", padx=5, pady=10)

preview_button = ctk.CTkButton(control_frame, text="Preview Sound", command=preview_sound)
preview_button.pack(side="left", padx=5, pady=10)

stop_button = ctk.CTkButton(control_frame, text="Stop Preview", command=stop_preview)
stop_button.pack(side="left", padx=5, pady=10)

generate_button = ctk.CTkButton(control_frame, text="Generate .keyclsound", command=generate_file)
generate_button.pack(side="right", padx=5, pady=10)

# Load root at start
load_repo("")

root.mainloop()
