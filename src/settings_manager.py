"""
KeyCL Settings Manager
Handles application settings persistence
"""

import json
import os


class SettingsManager:
    """Handles application settings persistence"""
    
    def __init__(self):
        self.settings_file = os.path.join(
            os.environ.get('USERPROFILE', os.path.expanduser('~')), 
            'KeyCl', 
            'settings.json'
        )
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        default_settings = {
            'volume': 0.5,
            'enabled': True,
            'current_sound': None,
            'theme': 'dark',
            'window_size': '1200x800',
            'first_run': True
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default_settings.update(loaded_settings)
                    print("Settings loaded successfully")
            else:
                print("No settings file found, using defaults")
        except Exception as e:
            print(f"Error loading settings: {e}")
            print("Using default settings")
        
        return default_settings
    
    def save_settings(self):
        """Save settings to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            print("Settings saved successfully")
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set a setting value and save"""
        self.settings[key] = value
        self.save_settings()
    
    def update(self, settings_dict):
        """Update multiple settings at once"""
        self.settings.update(settings_dict)
        self.save_settings()
    
    def reset_to_defaults(self):
        """Reset all settings to default values"""
        self.settings = {
            'volume': 0.5,
            'enabled': True,
            'current_sound': None,
            'theme': 'dark',
            'window_size': '1200x800',
            'first_run': False
        }
        self.save_settings()
        print("Settings reset to defaults")
    
    def get_settings_file_path(self):
        """Get the path to the settings file"""
        return self.settings_file
    
    def settings_exist(self):
        """Check if settings file exists"""
        return os.path.exists(self.settings_file)