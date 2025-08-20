#!/usr/bin/env python3
"""
KeyCL - Keyboard Sound Manager
Complete application with GUI, keyboard hooks, and system tray integration

What's new:
- Online Sound Library now browses **.keyclsound** packages and installs the audio from inside their `url`
- .keyclsound package support (install from file / browser)
- Lower-latency playback (smaller buffer, dedicated channel, debounce)
- pystray menu fixes

Base .keyclsound template (save as *.keyclsound):
--------------------------------------------------
{
  "title": "Retro Typewriter",
  "author": "OptionallyBlue",
  "description": "A vintage typewriter sound effect for your keyboard.",
  "tags": ["retro","mechanical","clicky"],
  "url": "https://raw.githubusercontent.com/OptionallyBlueStudios/KeyCL/main/sounds/typewriter.mp3"
}
--------------------------------------------------
"""

import customtkinter as ctk
import subprocess
import platform
import os
import threading
import time
import json
from tkinter import messagebox, filedialog
import pystray
from pystray import MenuItem as item
from PIL import Image
import pygame
import keyboard
import glob
import re

# New dependency for fetching/downloading
try:
    import requests
except ImportError:
    requests = None

GITHUB_CONTENTS_API = "https://api.github.com/repos/OptionallyBlueStudios/KeyCL/contents/sounds"


def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "sound"


def load_text(url: str, timeout=15):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def download_binary(url: str, dest_path: str, timeout=30):
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return dest_path


def parse_keyclsound(text: str) -> dict:
    """
    Accepts JSON or simple 'key: value' lines. Returns dict with:
    title, author, description, tags (list), url
    """
    text = text.strip()
    data = {}
    # Try JSON
    try:
        data = json.loads(text)
    except Exception:
        # Parse key: value lines
        for line in text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                data[k] = v

        # Coerce tags to list
        if "tags" in data and isinstance(data["tags"], str):
            data["tags"] = [t.strip() for t in data["tags"].split(",") if t.strip()]

    # Normalize
    data.setdefault("title", "Untitled Sound")
    data.setdefault("author", "")
    data.setdefault("description", "")
    tags = data.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    data["tags"] = tags
    data.setdefault("url", "")
    return data


class SoundManager:
    """Handles sound loading and playback"""

    def __init__(self):
        # Lower buffer -> lower latency
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=256)
        self.channel = pygame.mixer.Channel(0)  # dedicated channel for key sounds
        self.sounds = {}
        self.volume = 0.5
        self.enabled = True
        self.current_sound = None
        self.sounds_folder = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'KeyCl')
        os.makedirs(self.sounds_folder, exist_ok=True)
        self.load_sounds()

    def load_sounds(self):
        """Load all sound files from the sounds folder"""
        self.sounds.clear()
        sound_extensions = ['*.wav', '*.mp3', '*.ogg', '*.m4a']

        for ext in sound_extensions:
            for file_path in glob.glob(os.path.join(self.sounds_folder, ext)):
                try:
                    sound_name = os.path.splitext(os.path.basename(file_path))[0]
                    sound = pygame.mixer.Sound(file_path)
                    self.sounds[sound_name] = sound
                except pygame.error as e:
                    print(f"Could not load {file_path}: {e}")

    def play_sound(self, sound_name=None):
        """Play a sound effect with low-latency approach"""
        if not self.enabled:
            return

        if sound_name is None:
            sound_name = self.current_sound

        if sound_name and sound_name in self.sounds:
            try:
                sound = self.sounds[sound_name]
                sound.set_volume(self.volume)
                # Playing on dedicated channel replaces previous sound -> less lag/backlog
                self.channel.play(sound)
            except Exception as e:
                print(f"Error playing sound {sound_name}: {e}")

    def set_volume(self, volume):
        """Set playback volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))

    def set_current_sound(self, sound_name):
        """Set the current sound to play"""
        if sound_name in self.sounds:
            self.current_sound = sound_name

    def get_sound_list(self):
        """Get list of available sounds"""
        return list(self.sounds.keys())


class KeyboardHook:
    """Handles keyboard event monitoring"""

    def __init__(self, sound_manager):
        self.sound_manager = sound_manager
        self.enabled = True
        self.hook_active = False
        self.min_interval = 0.03  # 30 ms debounce to avoid excessive play/lag
        self._last_play_ts = 0.0

    def start_hook(self):
        """Start keyboard monitoring"""
        if not self.hook_active:
            self.hook_active = True
            keyboard.on_press(self._on_key_press)

    def stop_hook(self):
        """Stop keyboard monitoring"""
        if self.hook_active:
            self.hook_active = False
            keyboard.unhook_all()

    def _on_key_press(self, key):
        """Handle key press events"""
        if self.enabled and self.hook_active:
            # Filter out some keys to avoid excessive sound
            excluded_keys = ['shift', 'ctrl', 'alt', 'cmd', 'win', 'tab', 'caps lock']
            key_name = str(key).lower()

            if not any(excluded in key_name for excluded in excluded_keys):
                now = time.perf_counter()
                if (now - self._last_play_ts) >= self.min_interval:
                    self.sound_manager.play_sound()
                    self._last_play_ts = now


class SettingsManager:
    """Handles application settings persistence"""

    def __init__(self):
        self.settings_file = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'KeyCl', 'settings.json')
        self.settings = self.load_settings()

    def load_settings(self):
        """Load settings from file"""
        default_settings = {
            'volume': 0.5,
            'enabled': True,
            'current_sound': None,
            'theme': 'dark'
        }

        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default_settings.update(settings)
        except Exception as e:
            print(f"Error loading settings: {e}")

        return default_settings

    def save_settings(self):
        """Save settings to file"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()


class KeyCLApp:
    def __init__(self):
        self.root = None
        self.main_frame = None
        self.current_view = "home"
        self.sound_manager = SoundManager()
        self.keyboard_hook = KeyboardHook(self.sound_manager)
        self.settings_manager = SettingsManager()

        # Apply saved settings
        self.apply_saved_settings()

        # Start keyboard hook
        self.keyboard_hook.start_hook()

    def apply_saved_settings(self):
        """Apply settings loaded from file"""
        self.sound_manager.volume = self.settings_manager.get('volume', 0.5)
        self.sound_manager.enabled = self.settings_manager.get('enabled', True)
        self.keyboard_hook.enabled = self.sound_manager.enabled

        current_sound = self.settings_manager.get('current_sound')
        if current_sound:
            self.sound_manager.set_current_sound(current_sound)

    def setup_gui(self):
        """Initialize the GUI"""
        theme = self.settings_manager.get('theme', 'dark')
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("KeyCL - Keyboard Sound Manager")
        self.root.minsize(900, 650)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Create main layout
        self.create_sidebar()
        self.create_main_frame()
        self.show_home_view()

        # Handle window sizing
        self.setup_window_size()

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.root,
            width=200,
            corner_radius=0,
            fg_color=("#DBDBDB", "#212121")
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 5))
        self.sidebar.pack_propagate(False)

        # Sidebar title
        sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="KeyCL",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        sidebar_title.pack(pady=(20, 30), padx=20)

        # Status indicator
        status_text = "🔊 Enabled" if self.sound_manager.enabled else "🔇 Disabled"
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text=status_text,
            font=ctk.CTkFont(size=12),
            text_color="green" if self.sound_manager.enabled else "red"
        )
        self.status_label.pack(pady=(0, 20), padx=20)

        # Sidebar buttons
        self.btn_home = ctk.CTkButton(
            self.sidebar, text="Home", width=160, height=40,
            command=self.show_home_view
        )
        self.btn_home.pack(pady=5, padx=20)

        self.btn_sounds = ctk.CTkButton(
            self.sidebar, text="Sound Library", width=160, height=40,
            command=self.show_sounds_view
        )
        self.btn_sounds.pack(pady=5, padx=20)

        self.btn_settings = ctk.CTkButton(
            self.sidebar, text="Settings", width=160, height=40,
            command=self.show_settings_view
        )
        self.btn_settings.pack(pady=5, padx=20)

        self.btn_about = ctk.CTkButton(
            self.sidebar, text="About", width=160, height=40,
            command=self.show_about_view
        )
        self.btn_about.pack(pady=5, padx=20)

        # Store buttons for state management
        self.sidebar_buttons = {
            "home": self.btn_home,
            "sounds": self.btn_sounds,
            "settings": self.btn_settings,
            "about": self.btn_about
        }

    def create_main_frame(self):
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_frame.pack(side="right", expand=True, fill="both", padx=(0, 10), pady=10)

    def clear_main_frame(self):
        """Clear all widgets from main frame"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def update_button_states(self, active_button):
        """Update button appearance to show active state"""
        for name, button in self.sidebar_buttons.items():
            if name == active_button:
                button.configure(fg_color=("#3B8ED0", "#1F6AA5"))
            else:
                button.configure(fg_color=("#3A7EBF", "#1F538D"))

    def show_home_view(self):
        self.current_view = "home"
        self.update_button_states("home")
        self.clear_main_frame()

        # Welcome section
        welcome_label = ctk.CTkLabel(
            self.main_frame, text="KeyCL", font=ctk.CTkFont(size=32, weight="bold")
        )
        welcome_label.pack(pady=(50, 10))

        description_label = ctk.CTkLabel(
            self.main_frame,
            text="Keyboard Sound Manager\nAdd custom sounds to your typing experience",
            font=ctk.CTkFont(size=16), justify="center"
        )
        description_label.pack(pady=(0, 30))

        # Status and controls
        control_frame = ctk.CTkFrame(self.main_frame)
        control_frame.pack(pady=20, padx=40, fill="x")

        # Current status
        status_frame = ctk.CTkFrame(control_frame)
        status_frame.pack(pady=20, padx=20, fill="x")

        status_title = ctk.CTkLabel(
            status_frame, text="Current Status", font=ctk.CTkFont(size=16, weight="bold")
        )
        status_title.pack(pady=(10, 5))

        current_sound = self.sound_manager.current_sound or "None selected"
        self.current_sound_label = ctk.CTkLabel(
            status_frame, text=f"Active Sound: {current_sound}", font=ctk.CTkFont(size=14)
        )
        self.current_sound_label.pack(pady=5)

        volume_text = f"Volume: {int(self.sound_manager.volume * 100)}%"
        self.volume_label = ctk.CTkLabel(
            status_frame, text=volume_text, font=ctk.CTkFont(size=14)
        )
        self.volume_label.pack(pady=5)

        # Quick controls
        controls_frame = ctk.CTkFrame(control_frame)
        controls_frame.pack(pady=20, padx=20, fill="x")

        # Enable/Disable toggle
        self.toggle_button = ctk.CTkButton(
            controls_frame,
            text="Disable Sounds" if self.sound_manager.enabled else "Enable Sounds",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45, width=200,
            command=self.toggle_sounds,
            fg_color="red" if self.sound_manager.enabled else "green"
        )
        self.toggle_button.pack(pady=10)

        # Quick actions
        actions_frame = ctk.CTkFrame(controls_frame)
        actions_frame.pack(pady=10, fill="x")

        ctk.CTkButton(
            actions_frame, text="Open Sounds Folder", height=35, width=180,
            command=self.open_sounds_folder
        ).pack(side="left", padx=10, pady=10)

        ctk.CTkButton(
            actions_frame, text="Test Current Sound", height=35, width=180,
            command=self.test_sound
        ).pack(side="right", padx=10, pady=10)

    def show_sounds_view(self):
        self.current_view = "sounds"
        self.update_button_states("sounds")
        self.clear_main_frame()

        title_label = ctk.CTkLabel(
            self.main_frame, text="Sound Library", font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(30, 20))

        # Sound selection frame
        sound_frame = ctk.CTkFrame(self.main_frame)
        sound_frame.pack(pady=20, padx=40, fill="both", expand=True)

        # Refresh sounds button
        refresh_button = ctk.CTkButton(
            sound_frame, text="🔄 Refresh Sound List", height=35,
            command=self.refresh_sounds
        )
        refresh_button.pack(pady=10)

        # NEW: Browse Online Library (now scans .keyclsound files)
        browse_button = ctk.CTkButton(
            sound_frame, text="🌐 Browse Online Sound Library", height=35,
            command=self.browse_sound_library
        )
        browse_button.pack(pady=10)

        # NEW: Install from .keyclsound file
        install_button = ctk.CTkButton(
            sound_frame, text="📦 Install from .keyclsound File", height=35,
            command=self.install_keyclsound_from_file
        )
        install_button.pack(pady=10)

        # Sound list
        self.create_sound_list(sound_frame)

    def create_sound_list(self, parent):
        """Create scrollable sound list"""
        # Create scrollable frame
        self.sound_scroll_frame = ctk.CTkScrollableFrame(parent, height=400)
        self.sound_scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        sounds = self.sound_manager.get_sound_list()

        if not sounds:
            no_sounds_label = ctk.CTkLabel(
                self.sound_scroll_frame,
                text="No sounds found!\n\nAdd .wav, .mp3, .ogg, or .m4a files to your sounds folder.",
                font=ctk.CTkFont(size=14), justify="center"
            )
            no_sounds_label.pack(pady=50)
            return

        # Create sound buttons
        for sound_name in sounds:
            sound_button_frame = ctk.CTkFrame(self.sound_scroll_frame)
            sound_button_frame.pack(pady=5, padx=10, fill="x")

            # Sound name and select button
            sound_label = ctk.CTkLabel(
                sound_button_frame, text=sound_name, font=ctk.CTkFont(size=14)
            )
            sound_label.pack(side="left", padx=20, pady=10)

            # Current sound indicator
            if sound_name == self.sound_manager.current_sound:
                current_indicator = ctk.CTkLabel(
                    sound_button_frame, text="🎵", font=ctk.CTkFont(size=16)
                )
                current_indicator.pack(side="left", padx=5)

            # Buttons frame
            button_frame = ctk.CTkFrame(sound_button_frame)
            button_frame.pack(side="right", padx=10, pady=5)

            ctk.CTkButton(
                button_frame, text="Test", width=60, height=30,
                command=lambda name=sound_name: self.sound_manager.play_sound(name)
            ).pack(side="right", padx=2)

            ctk.CTkButton(
                button_frame, text="Select", width=60, height=30,
                command=lambda name=sound_name: self.select_sound(name)
            ).pack(side="right", padx=2)

    # -------- Online Library + .keyclsound Installers --------

    def browse_sound_library(self):
        """Browse and download sounds by scanning .keyclsound packages in the GitHub 'sounds' folder.
        Each .keyclsound is fetched, parsed, and the contained `url` is used to download the audio.
        """
        if requests is None:
            messagebox.showerror("Missing Dependency",
                                 "The 'requests' package is required.\nInstall it with:\n\npip install requests")
            return
        try:
            resp = requests.get(GITHUB_CONTENTS_API, timeout=15)
            resp.raise_for_status()
            files = resp.json()
        except Exception as e:
            messagebox.showerror("Network Error", f"Could not fetch library:\n{e}")
            return

        # Only .keyclsound packages
        keycls = [f for f in files if f.get("name", "").lower().endswith(".keyclsound")]
        if not keycls:
            messagebox.showinfo("No Packages", "No .keyclsound files were found in the online library.")
            return

        # Preload metadata for search/display (best effort)
        items = []
        for f in keycls:
            meta = None
            try:
                text = load_text(f.get("download_url"))
                meta = parse_keyclsound(text)
            except Exception:
                # Fallback to filename-based meta if parsing fails
                base = os.path.splitext(f.get("name", "Untitled"))[0]
                meta = {"title": base, "author": "", "description": "", "tags": [], "url": ""}
            items.append({
                "name": f.get("name", ""),
                "raw_url": f.get("download_url", ""),
                "meta": meta
            })

        # Build a browser window
        win = ctk.CTkToplevel(self.root)
        win.title("Browse Online Sound Library (.keyclsound)")
        win.geometry("760x560")

        # Search box
        search_var = ctk.StringVar(value="")
        search_entry = ctk.CTkEntry(win, textvariable=search_var, placeholder_text="Search by title, author, or tag...")
        search_entry.pack(pady=10, padx=10, fill="x")

        list_frame = ctk.CTkScrollableFrame(win)
        list_frame.pack(pady=10, padx=10, fill="both", expand=True)

        def render_list():
            for w in list_frame.winfo_children():
                w.destroy()
            query = search_var.get().strip().lower()

            for it in items:
                meta = it["meta"]
                title = meta.get("title", os.path.splitext(it["name"])[0])
                author = meta.get("author", "")
                tags = meta.get("tags", [])
                hay = " ".join([title, author, " ".join(tags)]).lower()
                if query and query not in hay:
                    continue

                row = ctk.CTkFrame(list_frame)
                row.pack(fill="x", padx=6, pady=4)

                left = ctk.CTkFrame(row, fg_color="transparent")
                left.pack(side="left", fill="x", expand=True)

                ctk.CTkLabel(left, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(8,2))
                subtitle = author or ""
                if tags:
                    subtitle = (subtitle + (" • " if subtitle else "")) + ", ".join(tags[:6])
                if subtitle:
                    ctk.CTkLabel(left, text=subtitle, font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=(0,8))

                def do_download(meta=meta):
                    # Install by using the parsed metadata (grabs audio from meta['url']).
                    self.install_keyclsound_from_metadata(meta)

                ctk.CTkButton(row, text="Download", width=110, command=do_download).pack(side="right", padx=10)

        render_list()

        def on_search_change(*_):
            render_list()

        search_var.trace_add("write", on_search_change)

    def install_keyclsound_from_file(self):
        """Open a .keyclsound file and install its referenced MP3 into the local library."""
        path = filedialog.askopenfilename(
            title="Select .keyclsound file",
            filetypes=[("KeyCL Sound Package", "*.keyclsound"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            meta = parse_keyclsound(text)
            self.install_keyclsound_from_metadata(meta)
        except Exception as e:
            messagebox.showerror("Install Failed", f"Could not install package:\n{e}")

    def install_keyclsound_from_metadata(self, meta: dict):
        """Given parsed metadata, download the audio from meta['url'] and save a .keyclsound alongside it."""
        url = meta.get("url", "").strip()
        title = sanitize_filename(meta.get("title", "Untitled Sound"))

        if not url:
            messagebox.showerror("Install Failed", "The package has no 'url' to download.")
            return
        if requests is None:
            messagebox.showerror("Missing Dependency",
                                 "The 'requests' package is required.\nInstall it with:\n\npip install requests")
            return

        try:
            # Decide a filename for the audio
            ext = os.path.splitext(url)[1].lower()
            if ext not in [".mp3", ".wav", ".ogg", ".m4a"]:
                # Fallback to .mp3 when extension is unknown
                ext = ".mp3"
            audio_filename = f"{title}{ext}"
            audio_path = os.path.join(self.sound_manager.sounds_folder, audio_filename)

            # Download audio
            download_binary(url, audio_path)

            # Save .keyclsound file (JSON format)
            pkg_path = os.path.join(self.sound_manager.sounds_folder, f"{title}.keyclsound")
            with open(pkg_path, "w", encoding="utf-8") as f:
                json.dump({
                    "title": meta.get("title", title),
                    "author": meta.get("author", ""),
                    "description": meta.get("description", ""),
                    "tags": meta.get("tags", []),
                    "url": url
                }, f, indent=2)

            # Reload and select as current
            self.refresh_sounds()
            # Select new one if present
            base_name = os.path.splitext(os.path.basename(audio_filename))[0]
            if base_name in self.sound_manager.sounds:
                self.select_sound(base_name)

            messagebox.showinfo("Installed", f"Installed: {title}")

        except Exception as e:
            messagebox.showerror("Install Failed", f"Download or install failed:\n{e}")

    # -------- end installers --------

    def show_settings_view(self):
        self.current_view = "settings"
        self.update_button_states("settings")
        self.clear_main_frame()

        title_label = ctk.CTkLabel(
            self.main_frame, text="Settings", font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(50, 30))

        settings_frame = ctk.CTkFrame(self.main_frame)
        settings_frame.pack(pady=20, padx=40, fill="x")

        # Volume control
        volume_label = ctk.CTkLabel(
            settings_frame, text="Volume:", font=ctk.CTkFont(size=14, weight="bold")
        )
        volume_label.pack(pady=(20, 5), anchor="w", padx=20)

        self.volume_var = ctk.DoubleVar(value=self.sound_manager.volume)
        volume_slider = ctk.CTkSlider(
            settings_frame, from_=0, to=1, number_of_steps=100,
            variable=self.volume_var, command=self.update_volume
        )
        volume_slider.pack(pady=(0, 10), padx=20, fill="x")

        self.volume_display = ctk.CTkLabel(
            settings_frame, text=f"{int(self.sound_manager.volume * 100)}%",
            font=ctk.CTkFont(size=12)
        )
        self.volume_display.pack(pady=(0, 20))

        # Theme setting
        theme_label = ctk.CTkLabel(
            settings_frame, text="Theme:", font=ctk.CTkFont(size=14, weight="bold")
        )
        theme_label.pack(pady=(10, 5), anchor="w", padx=20)

        theme_var = ctk.StringVar(value=self.settings_manager.get('theme', 'dark').title())
        theme_menu = ctk.CTkOptionMenu(
            settings_frame, values=["Dark", "Light", "System"],
            variable=theme_var, command=self.change_theme
        )
        theme_menu.pack(pady=(0, 20), padx=20, anchor="w")

        # Advanced settings
        advanced_label = ctk.CTkLabel(
            settings_frame, text="Advanced:", font=ctk.CTkFont(size=14, weight="bold")
        )
        advanced_label.pack(pady=(10, 5), anchor="w", padx=20)

        ctk.CTkButton(
            settings_frame, text="Reset All Settings", width=160, height=35,
            command=self.reset_settings, fg_color="orange"
        ).pack(pady=10, padx=20, anchor="w")

    def show_about_view(self):
        self.current_view = "about"
        self.update_button_states("about")
        self.clear_main_frame()

        title_label = ctk.CTkLabel(
            self.main_frame, text="About KeyCL", font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(50, 30))

        about_frame = ctk.CTkFrame(self.main_frame)
        about_frame.pack(pady=20, padx=40, fill="both", expand=True)

        about_text = f"""KeyCL - Keyboard Sound Manager

Version: 2.2.0
Platform: {platform.system()}

A comprehensive keyboard sound manager that adds 
custom sound effects to your typing experience.

Features:
• Custom sound library management
• Real-time keyboard sound playback
• System tray integration
• Volume and theme controls
• Cross-platform compatibility
• Supports WAV, MP3, OGG, M4A formats
• Browse & install sounds from online .keyclsound packages
• Install .keyclsound packages from file

Controls:
• Add sounds to your KeyCl folder
• Select active sound from library
• Adjust volume and toggle sounds
• Access via system tray

Icon: Pixel Vectors by Vecteezy https://www.vecteezy.com/free-vector/pixel

© 2025 OptionallyBlueStudios' KeyCL Project"""
        about_label = ctk.CTkLabel(
            about_frame, text=about_text, font=ctk.CTkFont(size=13), justify="center"
        )
        about_label.pack(pady=30, padx=20)

    # Action methods
    def open_sounds_folder(self):
        """Open the sounds folder"""
        try:
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{self.sound_manager.sounds_folder}"')
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", self.sound_manager.sounds_folder])
            else:  # Linux
                subprocess.Popen(["xdg-open", self.sound_manager.sounds_folder])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open sounds folder:\n{str(e)}")

    def refresh_sounds(self):
        """Refresh the sound library"""
        self.sound_manager.load_sounds()
        if self.current_view == "sounds":
            self.show_sounds_view()
        self.update_home_status()

    def select_sound(self, sound_name):
        """Select a sound as the current active sound"""
        self.sound_manager.set_current_sound(sound_name)
        self.settings_manager.set('current_sound', sound_name)
        self.update_home_status()
        if self.current_view == "sounds":
            self.show_sounds_view()
        messagebox.showinfo("Sound Selected", f"'{sound_name}' is now your active typing sound!")

    def test_sound(self):
        """Test the current sound"""
        if self.sound_manager.current_sound:
            self.sound_manager.play_sound()
        else:
            messagebox.showwarning("No Sound", "Please select a sound first!")

    def toggle_sounds(self):
        """Toggle sound playback on/off"""
        self.sound_manager.enabled = not self.sound_manager.enabled
        self.keyboard_hook.enabled = self.sound_manager.enabled
        self.settings_manager.set('enabled', self.sound_manager.enabled)

        # Update UI
        if hasattr(self, 'toggle_button'):
            self.toggle_button.configure(
                text="Disable Sounds" if self.sound_manager.enabled else "Enable Sounds",
                fg_color="red" if self.sound_manager.enabled else "green"
            )

        self.update_status_label()

    def update_volume(self, value):
        """Update volume setting"""
        self.sound_manager.set_volume(value)
        self.settings_manager.set('volume', value)
        if hasattr(self, 'volume_display'):
            self.volume_display.configure(text=f"{int(value * 100)}%")
        self.update_home_status()

    def change_theme(self, theme):
        """Change application theme"""
        theme_map = {"Dark": "dark", "Light": "light", "System": "system"}
        theme_key = theme_map.get(theme, "dark")
        ctk.set_appearance_mode(theme_key)
        self.settings_manager.set('theme', theme_key)

    def reset_settings(self):
        """Reset all settings to default"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings?"):
            # Reset to defaults
            self.sound_manager.volume = 0.5
            self.sound_manager.enabled = True
            self.keyboard_hook.enabled = True
            self.sound_manager.current_sound = None

            # Save defaults
            self.settings_manager.settings = {
                'volume': 0.5, 'enabled': True, 'current_sound': None, 'theme': 'dark'
            }
            self.settings_manager.save_settings()

            messagebox.showinfo("Settings Reset", "All settings have been reset to defaults!")
            self.show_settings_view()  # Refresh the settings view

    def update_status_label(self):
        """Update the sidebar status label"""
        if hasattr(self, 'status_label'):
            status_text = "🔊 Enabled" if self.sound_manager.enabled else "🔇 Disabled"
            self.status_label.configure(
                text=status_text,
                text_color="green" if self.sound_manager.enabled else "red"
            )

    def update_home_status(self):
        """Update home view status displays"""
        if hasattr(self, 'current_sound_label'):
            current_sound = self.sound_manager.current_sound or "None selected"
            self.current_sound_label.configure(text=f"Active Sound: {current_sound}")

        if hasattr(self, 'volume_label'):
            volume_text = f"Volume: {int(self.sound_manager.volume * 100)}%"
            self.volume_label.configure(text=volume_text)

    def setup_window_size(self):
        """Handle window sizing"""
        try:
            if platform.system() == "Windows":
                self.root.state("zoomed")
            else:
                self.center_window(1200, 800)
        except:
            self.center_window(1200, 800)

    def center_window(self, width, height):
        """Center window on screen"""
        self.root.geometry(f"{width}x{height}")
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def hide_window(self):
        """Hide window instead of closing"""
        self.root.withdraw()

    def show_window(self):
        """Show the window"""
        if self.root:
            self.root.deiconify()
            self.root.lift()
        else:
            self.setup_gui()
            self.run()

    def run(self):
        """Start the GUI"""
        if not self.root:
            self.setup_gui()
        self.root.mainloop()

    def quit_app(self):
        """Properly quit the application"""
        self.keyboard_hook.stop_hook()
        if self.root:
            self.root.quit()


class TrayManager:
    """Handles system tray functionality"""

    def __init__(self, app):
        self.app = app
        self.icon = None
        self.setup_tray()

    def setup_tray(self):
        """Setup system tray icon"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, "icon.png")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
            else:
                image = Image.new('RGB', (64, 64), color='blue')
        except Exception:
            image = Image.new('RGB', (64, 64), color='blue')

        # Build menu items in a list
        menu_items = [
            item("Open KeyCL", self.show_app),
            pystray.Menu.SEPARATOR,
            item(
                "Enable Sounds" if not self.app.sound_manager.enabled else "Disable Sounds",
                self.toggle_sounds
            ),
            item("Quick Volume", pystray.Menu(
                item("Volume 25%", lambda _=None, __=None: self.set_volume(0.25)),
                item("Volume 50%", lambda _=None, __=None: self.set_volume(0.50)),
                item("Volume 75%", lambda _=None, __=None: self.set_volume(0.75)),
                item("Volume 100%", lambda _=None, __=None: self.set_volume(1.0))
            ))
        ]

        # Add sound library submenu only if sounds exist
        sound_list = self.app.sound_manager.get_sound_list()
        if sound_list:
            # Inside setup_tray
            def make_setter(name):
                def _set(icon, item):
                    self.set_sound(name)
                return _set

            # Then when building the submenu:
            menu_items.append(item("Sound Library", pystray.Menu(
                *[item(sound_name, make_setter(sound_name)) for sound_name in sound_list[:10]]
            )))

        # Add the rest
        menu_items.extend([
            pystray.Menu.SEPARATOR,
            item("Refresh Sounds", self.refresh_sounds),
            item("Open Sounds Folder", self.open_sounds_folder),
            pystray.Menu.SEPARATOR,
            item("Quit", self.quit_app)
        ])

        # Build the actual menu
        menu = pystray.Menu(*menu_items)

        # Assign the icon
        self.icon = pystray.Icon("KeyCL", image, "KeyCL - Keyboard Sound Manager", menu)

    def show_app(self, icon=None, item=None):
        """Show the main application window"""
        threading.Thread(target=self.app.show_window).start()

    def toggle_sounds(self, icon=None, item=None):
        """Toggle sound playback"""
        self.app.toggle_sounds()
        # Recreate menu to update text
        self.setup_tray()

    def set_volume(self, volume):
        """Set volume from tray"""
        self.app.sound_manager.set_volume(volume)
        self.app.settings_manager.set('volume', volume)

    def set_sound(self, sound_name):
        """Set current sound from tray"""
        self.app.select_sound(sound_name)

    def refresh_sounds(self, icon=None, item=None):
        """Refresh sound library"""
        self.app.refresh_sounds()
        # Recreate menu to update sound list
        self.setup_tray()

    def open_sounds_folder(self, icon=None, item=None):
        """Open sounds folder from tray"""
        self.app.open_sounds_folder()

    def quit_app(self, icon=None, item=None):
        """Quit application from tray"""
        self.app.quit_app()
        self.icon.stop()

    def run(self):
        """Start the tray icon"""
        self.icon.run()


def main():
    """Main entry point"""
    # Create the main application
    app = KeyCLApp()

    # Create tray manager
    tray_manager = TrayManager(app)

    # Start tray icon in separate thread
    tray_thread = threading.Thread(target=tray_manager.run, daemon=True)
    tray_thread.start()

    # Start the GUI (this will block)
    app.setup_gui()
    app.run()


if __name__ == "__main__":
    main()
