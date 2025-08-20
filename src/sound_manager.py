"""
KeyCL Sound Manager
Handles sound loading, playback, and management
"""

import pygame
import os
import glob


class SoundManager:
    """Handles sound loading and playback"""
    
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.sounds = {}
        self.volume = 0.5
        self.enabled = True
        self.current_sound = None
        self.sounds_folder = os.path.join(
            os.environ.get('USERPROFILE', os.path.expanduser('~')), 'KeyCl'
        )
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
                    print(f"Loaded sound: {sound_name}")
                except pygame.error as e:
                    print(f"Could not load {file_path}: {e}")
    
    def play_sound(self, sound_name=None):
        """Play a sound effect"""
        if not self.enabled:
            return
            
        if sound_name is None:
            sound_name = self.current_sound
            
        if sound_name and sound_name in self.sounds:
            try:
                sound = self.sounds[sound_name]
                sound.set_volume(self.volume)
                sound.play()
            except Exception as e:
                print(f"Error playing sound {sound_name}: {e}")
    
    def set_volume(self, volume):
        """Set playback volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        print(f"Volume set to: {int(self.volume * 100)}%")
    
    def set_current_sound(self, sound_name):
        """Set the current sound to play"""
        if sound_name in self.sounds:
            self.current_sound = sound_name
            print(f"Current sound set to: {sound_name}")
        else:
            print(f"Sound '{sound_name}' not found in library")
    
    def get_sound_list(self):
        """Get list of available sounds"""
        return list(self.sounds.keys())
    
    def get_sounds_folder(self):
        """Get the sounds folder path"""
        return self.sounds_folder
    
    def toggle_enabled(self):
        """Toggle sound playback on/off"""
        self.enabled = not self.enabled
        status = "enabled" if self.enabled else "disabled"
        print(f"Sound playback {status}")
        return self.enabled