#!/usr/bin/env python3
"""
CW TRAINER - Apprendre le Code Morse
====================================
Version avec interface graphique moderne et soignée.

Installation: pip install pygame numpy
"""

import tkinter as tk
from tkinter import font as tkfont
import random
import threading
import time
import wave
import struct
import tempfile
import os
import math

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    AUDIO_METHOD = "pygame"
except:
    AUDIO_METHOD = None

if AUDIO_METHOD is None:
    try:
        import winsound
        AUDIO_METHOD = "winsound"
    except:
        pass

if AUDIO_METHOD is None:
    import platform
    if platform.system() == "Linux":
        AUDIO_METHOD = "aplay"
    elif platform.system() == "Darwin":
        AUDIO_METHOD = "afplay"


# === COULEURS THEME PRO ===
class Theme:
    # Fond principal - Gris charbon élégant
    BG_DARK = "#1a1a1a"
    BG_CARD = "#252525"
    BG_CARD_HOVER = "#303030"
    BG_INPUT = "#2a2a2a"
    
    # Accents - Or et blanc
    PRIMARY = "#d4af37"        # Or classique
    PRIMARY_GLOW = "#c9a227"
    SECONDARY = "#8b7355"      # Bronze
    SUCCESS = "#4a9f5b"        # Vert sobre
    ERROR = "#c45c5c"          # Rouge atténué
    WARNING = "#d4a437"        # Or foncé
    
    # Texte
    TEXT_PRIMARY = "#f5f5f5"   # Blanc cassé
    TEXT_SECONDARY = "#b0b0b0" # Gris clair
    TEXT_MUTED = "#707070"     # Gris moyen
    
    # Bordures et accents subtils
    BORDER = "#3a3a3a"
    ACCENT_LIGHT = "#e8e8e8"


# === CODE MORSE ===
MORSE_CODE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---',
    '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.'
}

# Dictionnaire inversé pour décoder
REVERSE_MORSE = {v: k for k, v in MORSE_CODE.items()}

LESSONS = [
    ("Niveau 1", ['E', 'T'], "Fondamentaux", "01"),
    ("Niveau 2", ['A', 'N'], "Point-Trait", "02"),
    ("Niveau 3", ['I', 'M'], "Doubles", "03"),
    ("Niveau 4", ['S', 'O'], "Signaux SOS", "04"),
    ("Niveau 5", ['R', 'K', 'U', 'D', 'G', 'W'], "Combinaisons", "05"),
    ("Niveau 6", ['H', 'B', 'L', 'F'], "4 éléments", "06"),
    ("Niveau 7", ['C', 'P', 'J', 'V', 'X', 'Y', 'Z', 'Q'], "Avancé", "07"),
    ("Niveau 8", ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'], "Chiffres", "08"),
    ("Alphabet", list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "A à Z complet", "09"),
    ("Expert", list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"), "Maîtrise totale", "10"),
]


class AudioPlayer:
    """Générateur audio"""
    
    def __init__(self, frequency=600, wpm=15):
        self.frequency = frequency
        self.wpm = wpm
        self.sample_rate = 44100
        self.is_playing = False
        self.temp_files = []
    
    def set_wpm(self, wpm):
        self.wpm = wpm
    
    def set_frequency(self, freq):
        self.frequency = freq
    
    def generate_wav_data(self, duration):
        if NUMPY_AVAILABLE:
            num_samples = int(self.sample_rate * duration)
            t = np.linspace(0, duration, num_samples, False)
            tone = np.sin(2 * np.pi * self.frequency * t)
            attack = int(0.008 * self.sample_rate)
            release = int(0.008 * self.sample_rate)
            envelope = np.ones(num_samples)
            if attack > 0:
                envelope[:attack] = np.linspace(0, 1, attack)
            if release > 0:
                envelope[-release:] = np.linspace(1, 0, release)
            audio = (tone * envelope * 0.5 * 32767).astype(np.int16)
            return audio.tobytes()
        else:
            num_samples = int(self.sample_rate * duration)
            data = []
            for i in range(num_samples):
                t = i / self.sample_rate
                env = 1.0
                attack_samples = int(0.008 * self.sample_rate)
                release_samples = int(0.008 * self.sample_rate)
                if i < attack_samples:
                    env = i / attack_samples
                elif i > num_samples - release_samples:
                    env = (num_samples - i) / release_samples
                sample = int(32767 * 0.5 * env * math.sin(2 * math.pi * self.frequency * t))
                data.append(struct.pack('<h', sample))
            return b''.join(data)
    
    def create_wav_file(self, duration):
        data = self.generate_wav_data(duration)
        fd, filepath = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        self.temp_files.append(filepath)
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(data)
        return filepath
    
    def play_tone(self, duration):
        if AUDIO_METHOD == "pygame":
            wav_path = self.create_wav_file(duration)
            sound = pygame.mixer.Sound(wav_path)
            sound.play()
            time.sleep(duration)
        elif AUDIO_METHOD == "winsound":
            wav_path = self.create_wav_file(duration)
            import winsound
            winsound.PlaySound(wav_path, winsound.SND_FILENAME)
        elif AUDIO_METHOD in ["aplay", "afplay"]:
            wav_path = self.create_wav_file(duration)
            os.system(f"{AUDIO_METHOD} {wav_path} 2>/dev/null")
        else:
            time.sleep(duration)
    
    def play_morse(self, text, callback=None):
        self.is_playing = True
        
        def _play():
            dot_duration = 1.2 / self.wpm
            dash_duration = dot_duration * 3
            symbol_gap = dot_duration
            char_gap = dot_duration * 3
            
            for char in text.upper():
                if not self.is_playing:
                    break
                morse = MORSE_CODE.get(char, '')
                if not morse:
                    continue
                for i, symbol in enumerate(morse):
                    if not self.is_playing:
                        break
                    if symbol == '.':
                        self.play_tone(dot_duration)
                    elif symbol == '-':
                        self.play_tone(dash_duration)
                    if i < len(morse) - 1:
                        time.sleep(symbol_gap)
                time.sleep(char_gap)
            
            self.is_playing = False
            self.cleanup()
            if callback:
                callback()
        
        threading.Thread(target=_play, daemon=True).start()
    
    def stop(self):
        self.is_playing = False
    
    def cleanup(self):
        for f in self.temp_files:
            try:
                os.remove(f)
            except:
                pass
        self.temp_files = []


class RoundedButton(tk.Canvas):
    """Bouton avec coins arrondis"""
    
    def __init__(self, parent, text, command, width=120, height=40, 
                 bg_color=Theme.BG_CARD, fg_color=Theme.TEXT_PRIMARY,
                 hover_color=Theme.BG_CARD_HOVER, font_size=11, radius=10, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        bg=parent.cget('bg'), highlightthickness=0, **kwargs)
        
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.fg_color = fg_color
        self.radius = radius
        self.text = text
        self.font_size = font_size
        self._width = width
        self._height = height
        
        self.draw(bg_color)
        
        self.bind('<Enter>', lambda e: self.draw(hover_color))
        self.bind('<Leave>', lambda e: self.draw(bg_color))
        self.bind('<Button-1>', lambda e: self.on_click())
    
    def draw(self, color):
        self.delete('all')
        self.create_rounded_rect(2, 2, self._width-2, self._height-2, self.radius, fill=color, outline='')
        self.create_text(self._width//2, self._height//2, text=self.text, 
                        fill=self.fg_color, font=('Segoe UI', self.font_size, 'bold'))
    
    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def on_click(self):
        if self.command:
            self.command()


class GlowingOrb(tk.Canvas):
    """Orbe lumineux animé"""
    
    def __init__(self, parent, size=150):
        super().__init__(parent, width=size, height=size, bg=Theme.BG_DARK, highlightthickness=0)
        self.size = size
        self.center = size // 2
        self.is_active = False
        self.pulse_phase = 0
        self.draw_idle()
    
    def draw_idle(self):
        self.delete('all')
        # Cercles concentriques sombres
        for i in range(5, 0, -1):
            alpha = int(30 + i * 10)
            r = 20 + i * 12
            color = self._adjust_brightness(Theme.BG_CARD, 1 + i * 0.1)
            self.create_oval(
                self.center - r, self.center - r,
                self.center + r, self.center + r,
                fill=color, outline=''
            )
        # Point central
        self.create_oval(
            self.center - 8, self.center - 8,
            self.center + 8, self.center + 8,
            fill=Theme.TEXT_MUTED, outline=''
        )
    
    def draw_active(self, intensity=1.0):
        self.delete('all')
        # Glow externe
        for i in range(8, 0, -1):
            r = 25 + i * 10
            alpha = 0.1 * (9 - i) * intensity
            color = self._blend_color(Theme.BG_DARK, Theme.PRIMARY, alpha)
            self.create_oval(
                self.center - r, self.center - r,
                self.center + r, self.center + r,
                fill=color, outline=''
            )
        # Coeur brillant
        self.create_oval(
            self.center - 20, self.center - 20,
            self.center + 20, self.center + 20,
            fill=Theme.PRIMARY, outline=''
        )
        # Point blanc central
        self.create_oval(
            self.center - 8, self.center - 8,
            self.center + 8, self.center + 8,
            fill='#ffffff', outline=''
        )
    
    def set_active(self, active):
        self.is_active = active
        if active:
            self.draw_active()
        else:
            self.draw_idle()
    
    def _adjust_brightness(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _blend_color(self, color1, color2, alpha):
        c1 = [int(color1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
        c2 = [int(color2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
        blended = [int(c1[i] * (1 - alpha) + c2[i] * alpha) for i in range(3)]
        return f'#{blended[0]:02x}{blended[1]:02x}{blended[2]:02x}'


class MorseVisualizer(tk.Canvas):
    """Visualiseur du code morse avec points et traits animés"""
    
    def __init__(self, parent, width=300, height=50):
        super().__init__(parent, width=width, height=height, bg=Theme.BG_DARK, highlightthickness=0)
        self._width = width
        self._height = height
    
    def show_morse(self, code, color=Theme.PRIMARY):
        self.delete('all')
        if not code:
            return
        
        total_width = 0
        elements = []
        for symbol in code:
            if symbol == '.':
                elements.append(('dot', 14))
                total_width += 14
            elif symbol == '-':
                elements.append(('dash', 40))
                total_width += 40
            total_width += 10  # gap
        total_width -= 10
        
        x = (self._width - total_width) // 2
        y = self._height // 2
        
        for elem_type, width in elements:
            if elem_type == 'dot':
                # Glow
                self.create_oval(x-4, y-11, x+width+4, y+11, fill=self._dim_color(color, 0.3), outline='')
                # Point
                self.create_oval(x, y-7, x+width, y+7, fill=color, outline='')
            else:
                # Glow
                self.create_rectangle(x-2, y-9, x+width+2, y+9, fill=self._dim_color(color, 0.3), outline='')
                # Trait
                self.create_rectangle(x, y-5, x+width, y+5, fill=color, outline='')
            x += width + 10
    
    def clear(self):
        self.delete('all')
    
    def _dim_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        return f'#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}'


class StatCard(tk.Frame):
    """Carte de statistique stylisée"""
    
    def __init__(self, parent, label, value, color=Theme.PRIMARY):
        super().__init__(parent, bg=Theme.BG_CARD, padx=20, pady=12)
        
        self.label_widget = tk.Label(
            self, text=label,
            font=('Segoe UI', 9),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        )
        self.label_widget.pack()
        
        self.value_widget = tk.Label(
            self, text=str(value),
            font=('Segoe UI', 22, 'bold'),
            bg=Theme.BG_CARD, fg=color
        )
        self.value_widget.pack()
    
    def update_value(self, value, color=None):
        self.value_widget.config(text=str(value))
        if color:
            self.value_widget.config(fg=color)


class MorseTrainer:
    """Application principale"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CW Trainer - Professional Morse Code Training")
        self.root.geometry("1000x900")
        self.root.configure(bg=Theme.BG_DARK)
        self.root.resizable(True, True)
        self.root.minsize(900, 800)
        
        # Centrer la fenêtre
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 1000) // 2
        y = (self.root.winfo_screenheight() - 900) // 2
        self.root.geometry(f"+{x}+{y}")
        
        # Variables
        self.wpm = tk.IntVar(value=15)
        self.frequency = tk.IntVar(value=600)
        self.score_correct = 0
        self.score_total = 0
        self.streak = 0
        self.best_streak = 0
        self.current_char = ''
        self.current_lesson = 0
        self.lesson_chars = []
        self.history = []
        
        # Audio
        self.audio = AudioPlayer()
        
        # Frame principal
        self.main_frame = tk.Frame(self.root, bg=Theme.BG_DARK)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.show_menu()
    
    def clear_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
    
    def show_menu(self):
        """Menu principal avec design moderne - Alphabet à droite"""
        self.clear_frame()
        
        # Header avec titre stylisé
        header = tk.Frame(self.main_frame, bg=Theme.BG_DARK)
        header.pack(fill=tk.X, pady=(20, 10))
        
        # Logo/Titre
        title_frame = tk.Frame(header, bg=Theme.BG_DARK)
        title_frame.pack()
        
        tk.Label(
            title_frame, text="━━━",
            font=('Consolas', 20),
            bg=Theme.BG_DARK, fg=Theme.PRIMARY
        ).pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(
            title_frame, text="CW TRAINER",
            font=('Georgia', 32, 'bold'),
            bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY
        ).pack(side=tk.LEFT)
        
        tk.Label(
            title_frame, text="━━━",
            font=('Consolas', 20),
            bg=Theme.BG_DARK, fg=Theme.PRIMARY
        ).pack(side=tk.LEFT, padx=(15, 0))
        
        # Sous-titre
        tk.Label(
            header, text="Professional Morse Code Training",
            font=('Georgia', 10, 'italic'),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED
        ).pack(pady=(5, 0))
        
        # Status audio
        status_color = Theme.SUCCESS if AUDIO_METHOD else Theme.ERROR
        status_text = "● Audio Ready" if AUDIO_METHOD else "○ Audio Unavailable"
        tk.Label(
            header, text=status_text,
            font=('Segoe UI', 9),
            bg=Theme.BG_DARK, fg=status_color
        ).pack(pady=(5, 0))
        
        # ========== CONTENEUR PRINCIPAL 2 COLONNES ==========
        main_container = tk.Frame(self.main_frame, bg=Theme.BG_DARK)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # === COLONNE GAUCHE (Leçons + Paramètres) ===
        left_column = tk.Frame(main_container, bg=Theme.BG_DARK)
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Titre section leçons
        tk.Label(
            left_column, text="SÉLECTIONNER UN NIVEAU",
            font=('Segoe UI', 10, 'bold'),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED
        ).pack(pady=(0, 10))
        
        # Grille des leçons
        lessons_frame = tk.Frame(left_column, bg=Theme.BG_DARK)
        lessons_frame.pack()
        
        for i, (name, chars, desc, num) in enumerate(LESSONS):
            row, col = divmod(i, 2)
            
            card = tk.Frame(lessons_frame, bg=Theme.BG_CARD, padx=12, pady=10)
            card.grid(row=row, column=col, padx=5, pady=4, sticky='nsew')
            
            # Header de la carte
            card_header = tk.Frame(card, bg=Theme.BG_CARD)
            card_header.pack(fill=tk.X)
            
            tk.Label(
                card_header, text=num,
                font=('Georgia', 12, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.PRIMARY,
                width=3
            ).pack(side=tk.LEFT)
            
            tk.Label(
                card_header, text="│",
                font=('Consolas', 12),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
            ).pack(side=tk.LEFT, padx=5)
            
            tk.Label(
                card_header, text=name,
                font=('Segoe UI', 10, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY
            ).pack(side=tk.LEFT)
            
            tk.Label(
                card, text=desc,
                font=('Segoe UI', 8),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
            ).pack(anchor='w', pady=(5, 2))
            
            chars_preview = ' '.join(chars[:5]) + ('...' if len(chars) > 5 else '')
            tk.Label(
                card, text=chars_preview,
                font=('Consolas', 9),
                bg=Theme.BG_CARD, fg=Theme.SECONDARY
            ).pack(anchor='w')
            
            for widget in [card, card_header] + list(card.winfo_children()) + list(card_header.winfo_children()):
                widget.bind('<Enter>', lambda e, c=card: c.config(bg=Theme.BG_CARD_HOVER) or self._update_children_bg(c, Theme.BG_CARD_HOVER))
                widget.bind('<Leave>', lambda e, c=card: c.config(bg=Theme.BG_CARD) or self._update_children_bg(c, Theme.BG_CARD))
                widget.bind('<Button-1>', lambda e, idx=i: self.start_practice(idx))
                widget.config(cursor='hand2')
        
        # Paramètres
        settings_frame = tk.Frame(left_column, bg=Theme.BG_CARD, padx=20, pady=12)
        settings_frame.pack(fill=tk.X, pady=(15, 10))
        
        tk.Label(
            settings_frame, text="PARAMÈTRES",
            font=('Segoe UI', 9, 'bold'),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        ).pack(pady=(0, 8))
        
        params_row = tk.Frame(settings_frame, bg=Theme.BG_CARD)
        params_row.pack()
        
        # WPM
        wpm_frame = tk.Frame(params_row, bg=Theme.BG_CARD)
        wpm_frame.pack(side=tk.LEFT, padx=15)
        
        tk.Label(
            wpm_frame, text="Vitesse (WPM)",
            font=('Segoe UI', 8),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        ).pack()
        
        tk.Scale(
            wpm_frame, from_=5, to=25, orient=tk.HORIZONTAL,
            variable=self.wpm, length=120, width=10,
            bg=Theme.BG_CARD, fg=Theme.PRIMARY,
            highlightthickness=0, troughcolor=Theme.BG_INPUT,
            activebackground=Theme.PRIMARY, sliderrelief=tk.FLAT
        ).pack()
        
        # Fréquence
        freq_frame = tk.Frame(params_row, bg=Theme.BG_CARD)
        freq_frame.pack(side=tk.LEFT, padx=15)
        
        tk.Label(
            freq_frame, text="Fréquence (Hz)",
            font=('Segoe UI', 8),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        ).pack()
        
        tk.Scale(
            freq_frame, from_=400, to=800, orient=tk.HORIZONTAL,
            variable=self.frequency, length=120, width=10,
            bg=Theme.BG_CARD, fg=Theme.PRIMARY,
            highlightthickness=0, troughcolor=Theme.BG_INPUT,
            activebackground=Theme.PRIMARY, sliderrelief=tk.FLAT
        ).pack()
        
        # Boutons
        btn_frame = tk.Frame(left_column, bg=Theme.BG_DARK)
        btn_frame.pack(pady=10)
        
        RoundedButton(
            btn_frame, "Manipulateur", self.show_keyer,
            width=120, height=40, bg_color=Theme.PRIMARY,
            fg_color=Theme.BG_DARK, hover_color=Theme.SECONDARY
        ).pack(side=tk.LEFT, padx=5)
        
        RoundedButton(
            btn_frame, "Référence", self.show_reference,
            width=120, height=40, bg_color=Theme.BG_CARD,
            fg_color=Theme.PRIMARY, hover_color=Theme.BG_CARD_HOVER
        ).pack(side=tk.LEFT, padx=5)
        
        RoundedButton(
            btn_frame, "Test Audio", self.test_sound,
            width=120, height=40, bg_color=Theme.BG_CARD,
            fg_color=Theme.SUCCESS, hover_color=Theme.BG_CARD_HOVER
        ).pack(side=tk.LEFT, padx=5)
        
        # === COLONNE DROITE (Alphabet Morse) ===
        right_column = tk.Frame(main_container, bg=Theme.BG_CARD, padx=20, pady=15)
        right_column.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # Titre
        tk.Label(
            right_column, text="━ ALPHABET MORSE ━",
            font=('Georgia', 11, 'bold'),
            bg=Theme.BG_CARD, fg=Theme.PRIMARY
        ).pack(pady=(0, 15))
        
        # Grille des lettres A-Z (disposition verticale 7 colonnes)
        letters_grid = tk.Frame(right_column, bg=Theme.BG_CARD)
        letters_grid.pack()
        
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i, char in enumerate(letters):
            row, col = divmod(i, 7)
            
            cell = tk.Frame(letters_grid, bg=Theme.BG_CARD)
            cell.grid(row=row, column=col, padx=4, pady=3)
            
            tk.Label(
                cell, text=char,
                font=('Georgia', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.PRIMARY,
                width=2
            ).pack()
            
            tk.Label(
                cell, text=MORSE_CODE[char],
                font=('Consolas', 8),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
            ).pack()
            
            for widget in [cell] + list(cell.winfo_children()):
                widget.bind('<Button-1>', lambda e, c=char: self.play_char(c))
                widget.bind('<Enter>', lambda e, c=cell: self._highlight_cell(c, True))
                widget.bind('<Leave>', lambda e, c=cell: self._highlight_cell(c, False))
                widget.config(cursor='hand2')
        
        # Séparateur
        tk.Frame(right_column, bg=Theme.BORDER, height=1).pack(fill=tk.X, pady=12)
        
        # Titre chiffres
        tk.Label(
            right_column, text="CHIFFRES",
            font=('Georgia', 9),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        ).pack(pady=(0, 8))
        
        # Grille des chiffres 0-9 (2 lignes de 5)
        numbers_grid = tk.Frame(right_column, bg=Theme.BG_CARD)
        numbers_grid.pack()
        
        for i, char in enumerate("0123456789"):
            row, col = divmod(i, 5)
            
            cell = tk.Frame(numbers_grid, bg=Theme.BG_CARD)
            cell.grid(row=row, column=col, padx=6, pady=3)
            
            tk.Label(
                cell, text=char,
                font=('Georgia', 11, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.SECONDARY,
                width=2
            ).pack()
            
            tk.Label(
                cell, text=MORSE_CODE[char],
                font=('Consolas', 7),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
            ).pack()
            
            for widget in [cell] + list(cell.winfo_children()):
                widget.bind('<Button-1>', lambda e, c=char: self.play_char(c))
                widget.bind('<Enter>', lambda e, c=cell: self._highlight_cell(c, True))
                widget.bind('<Leave>', lambda e, c=cell: self._highlight_cell(c, False))
                widget.config(cursor='hand2')
        
        # Info
        tk.Label(
            right_column,
            text="Cliquez pour écouter",
            font=('Segoe UI', 8, 'italic'),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        ).pack(pady=(12, 0))
    
    def _highlight_cell(self, cell, hover):
        """Met en surbrillance une cellule au survol"""
        color = Theme.BG_CARD_HOVER if hover else Theme.BG_CARD
        cell.config(bg=color)
        for child in cell.winfo_children():
            try:
                child.config(bg=color)
            except:
                pass
    
    def play_char(self, char):
        """Joue un caractère morse"""
        self.audio.set_wpm(self.wpm.get())
        self.audio.set_frequency(self.frequency.get())
        self.audio.play_morse(char)
    
    def _update_children_bg(self, parent, color):
        for child in parent.winfo_children():
            try:
                child.config(bg=color)
                self._update_children_bg(child, color)
            except:
                pass
    
    def test_sound(self):
        self.audio.set_wpm(self.wpm.get())
        self.audio.set_frequency(self.frequency.get())
        self.audio.play_morse("OK")
    
    def show_keyer(self):
        """Mode manipulateur - Utiliser ESPACE comme clé morse"""
        self.clear_frame()
        
        # Variables pour le keyer
        self.key_press_time = 0
        self.key_release_time = 0
        self.current_morse = ""
        self.decoded_text = ""
        self.is_key_pressed = False
        self.tone_playing = False
        self.char_timeout_id = None
        self.word_timeout_id = None
        
        # Timing basé sur WPM
        dot_duration = 1.2 / self.wpm.get()
        self.dot_threshold = dot_duration * 2  # Seuil point/trait
        self.char_gap = dot_duration * 3       # Pause entre caractères
        self.word_gap = dot_duration * 7       # Pause entre mots
        
        # Header
        header = tk.Frame(self.main_frame, bg=Theme.BG_DARK)
        header.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        back_btn = tk.Label(
            header, text="← Retour",
            font=('Segoe UI', 11),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED,
            cursor='hand2'
        )
        back_btn.pack(side=tk.LEFT)
        back_btn.bind('<Button-1>', lambda e: self.show_menu())
        back_btn.bind('<Enter>', lambda e: back_btn.config(fg=Theme.PRIMARY))
        back_btn.bind('<Leave>', lambda e: back_btn.config(fg=Theme.TEXT_MUTED))
        
        tk.Label(
            header, text="MANIPULATEUR MORSE",
            font=('Georgia', 16, 'bold'),
            bg=Theme.BG_DARK, fg=Theme.PRIMARY
        ).pack(side=tk.RIGHT)
        
        # Instructions
        instructions = tk.Frame(self.main_frame, bg=Theme.BG_CARD, padx=20, pady=15)
        instructions.pack(fill=tk.X, padx=30, pady=10)
        
        tk.Label(
            instructions,
            text="Utilisez la touche ESPACE comme manipulateur morse",
            font=('Segoe UI', 11, 'bold'),
            bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY
        ).pack()
        
        tk.Label(
            instructions,
            text="Appui court = Point (·)  |  Appui long = Trait (−)  |  Pause = Validation",
            font=('Segoe UI', 9),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        ).pack(pady=(5, 0))
        
        # Zone principale
        main_zone = tk.Frame(self.main_frame, bg=Theme.BG_DARK)
        main_zone.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Indicateur visuel du manipulateur
        self.keyer_canvas = tk.Canvas(
            main_zone, width=200, height=200,
            bg=Theme.BG_DARK, highlightthickness=0
        )
        self.keyer_canvas.pack(pady=20)
        self._draw_keyer_indicator(False)
        
        # Affichage du code morse en cours
        morse_frame = tk.Frame(main_zone, bg=Theme.BG_CARD, padx=30, pady=15)
        morse_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            morse_frame, text="CODE EN COURS",
            font=('Segoe UI', 9),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        ).pack()
        
        self.morse_display = tk.Label(
            morse_frame, text="",
            font=('Consolas', 36, 'bold'),
            bg=Theme.BG_CARD, fg=Theme.PRIMARY,
            width=15
        )
        self.morse_display.pack(pady=10)
        
        # Caractère décodé
        self.char_display = tk.Label(
            morse_frame, text="?",
            font=('Georgia', 48, 'bold'),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        )
        self.char_display.pack()
        
        # Texte décodé complet
        text_frame = tk.Frame(main_zone, bg=Theme.BG_CARD, padx=20, pady=15)
        text_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            text_frame, text="TEXTE DÉCODÉ",
            font=('Segoe UI', 9),
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
        ).pack()
        
        self.text_display = tk.Label(
            text_frame, text="",
            font=('Consolas', 18),
            bg=Theme.BG_CARD, fg=Theme.SUCCESS,
            wraplength=500
        )
        self.text_display.pack(pady=10)
        
        # Bouton effacer
        btn_frame = tk.Frame(main_zone, bg=Theme.BG_DARK)
        btn_frame.pack(pady=10)
        
        RoundedButton(
            btn_frame, "Effacer", self._clear_keyer,
            width=100, height=35, bg_color=Theme.BG_CARD,
            fg_color=Theme.ERROR, hover_color=Theme.BG_CARD_HOVER
        ).pack(side=tk.LEFT, padx=5)
        
        # Info WPM
        tk.Label(
            main_zone,
            text=f"Vitesse: {self.wpm.get()} WPM | Seuil point/trait: {self.dot_threshold*1000:.0f}ms",
            font=('Segoe UI', 9),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED
        ).pack(pady=10)
        
        # Bind des touches
        self.root.bind('<KeyPress-space>', self._on_key_press)
        self.root.bind('<KeyRelease-space>', self._on_key_release)
        self.root.focus_set()
    
    def _draw_keyer_indicator(self, pressed):
        """Dessine l'indicateur du manipulateur"""
        self.keyer_canvas.delete('all')
        
        cx, cy = 100, 100
        
        if pressed:
            # État pressé - illuminé
            # Glow externe
            for i in range(5, 0, -1):
                r = 60 + i * 8
                alpha = 0.15 * (6 - i)
                color = self._blend_colors(Theme.BG_DARK, Theme.PRIMARY, alpha)
                self.keyer_canvas.create_oval(
                    cx - r, cy - r, cx + r, cy + r,
                    fill=color, outline=''
                )
            # Cercle principal
            self.keyer_canvas.create_oval(
                cx - 50, cy - 50, cx + 50, cy + 50,
                fill=Theme.PRIMARY, outline=Theme.PRIMARY, width=3
            )
            # Centre blanc
            self.keyer_canvas.create_oval(
                cx - 20, cy - 20, cx + 20, cy + 20,
                fill='#ffffff', outline=''
            )
        else:
            # État relâché
            self.keyer_canvas.create_oval(
                cx - 60, cy - 60, cx + 60, cy + 60,
                fill=Theme.BG_CARD, outline=Theme.BORDER, width=2
            )
            self.keyer_canvas.create_oval(
                cx - 40, cy - 40, cx + 40, cy + 40,
                fill=Theme.BG_DARK, outline=Theme.TEXT_MUTED, width=1
            )
            self.keyer_canvas.create_text(
                cx, cy, text="ESPACE",
                font=('Segoe UI', 10, 'bold'),
                fill=Theme.TEXT_MUTED
            )
    
    def _blend_colors(self, color1, color2, alpha):
        """Mélange deux couleurs"""
        c1 = [int(color1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
        c2 = [int(color2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
        blended = [int(c1[i] * (1 - alpha) + c2[i] * alpha) for i in range(3)]
        return f'#{blended[0]:02x}{blended[1]:02x}{blended[2]:02x}'
    
    def _on_key_press(self, event):
        """Appelé quand ESPACE est pressé"""
        if self.is_key_pressed:
            return  # Éviter les répétitions
        
        self.is_key_pressed = True
        self.key_press_time = time.time()
        
        # Annuler les timeouts en cours
        if self.char_timeout_id:
            self.root.after_cancel(self.char_timeout_id)
            self.char_timeout_id = None
        if self.word_timeout_id:
            self.root.after_cancel(self.word_timeout_id)
            self.word_timeout_id = None
        
        # Affichage visuel
        self._draw_keyer_indicator(True)
        
        # Jouer le son
        self._start_tone()
    
    def _on_key_release(self, event):
        """Appelé quand ESPACE est relâché"""
        if not self.is_key_pressed:
            return
        
        self.is_key_pressed = False
        self.key_release_time = time.time()
        
        # Arrêter le son
        self._stop_tone()
        
        # Calculer la durée
        duration = self.key_release_time - self.key_press_time
        
        # Déterminer point ou trait
        if duration < self.dot_threshold:
            self.current_morse += "."
        else:
            self.current_morse += "-"
        
        # Affichage visuel
        self._draw_keyer_indicator(False)
        self.morse_display.config(text=self.current_morse)
        
        # Prévisualiser le caractère
        if self.current_morse in REVERSE_MORSE:
            self.char_display.config(
                text=REVERSE_MORSE[self.current_morse],
                fg=Theme.SUCCESS
            )
        else:
            self.char_display.config(text="?", fg=Theme.TEXT_MUTED)
        
        # Programmer la validation du caractère après une pause
        self.char_timeout_id = self.root.after(
            int(self.char_gap * 1000),
            self._validate_char
        )
    
    def _start_tone(self):
        """Démarre la tonalité en continu"""
        self.tone_playing = True
        
        def _play_continuous():
            sample_rate = 44100
            
            while self.tone_playing:
                # Générer un petit segment de son
                duration = 0.1  # 100ms segments
                
                if NUMPY_AVAILABLE:
                    num_samples = int(sample_rate * duration)
                    t = np.linspace(0, duration, num_samples, False)
                    tone = np.sin(2 * np.pi * self.frequency.get() * t)
                    
                    # Envelope douce
                    envelope = np.ones(num_samples)
                    fade = int(0.005 * sample_rate)
                    if fade > 0 and fade < num_samples // 2:
                        envelope[:fade] = np.linspace(0, 1, fade)
                        envelope[-fade:] = np.linspace(1, 0, fade)
                    
                    audio = (tone * envelope * 0.5 * 32767).astype(np.int16)
                    audio_bytes = audio.tobytes()
                else:
                    # Sans numpy
                    num_samples = int(sample_rate * duration)
                    audio_bytes = b''
                    for i in range(num_samples):
                        t = i / sample_rate
                        sample = int(32767 * 0.5 * math.sin(2 * math.pi * self.frequency.get() * t))
                        audio_bytes += struct.pack('<h', sample)
                
                # Créer fichier temporaire
                fd, filepath = tempfile.mkstemp(suffix='.wav')
                os.close(fd)
                
                try:
                    with wave.open(filepath, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(sample_rate)
                        wav_file.writeframes(audio_bytes)
                    
                    if AUDIO_METHOD == "pygame":
                        sound = pygame.mixer.Sound(filepath)
                        sound.play()
                        time.sleep(duration * 0.9)  # Légère superposition
                    elif AUDIO_METHOD == "winsound":
                        import winsound
                        winsound.PlaySound(filepath, winsound.SND_FILENAME)
                    elif AUDIO_METHOD in ["aplay", "afplay"]:
                        os.system(f"{AUDIO_METHOD} {filepath} 2>/dev/null &")
                        time.sleep(duration * 0.9)
                    else:
                        time.sleep(duration)
                finally:
                    try:
                        os.remove(filepath)
                    except:
                        pass
        
        # Lancer dans un thread séparé
        self.tone_thread = threading.Thread(target=_play_continuous, daemon=True)
        self.tone_thread.start()
    
    def _stop_tone(self):
        """Arrête la tonalité"""
        self.tone_playing = False
        
        if AUDIO_METHOD == "pygame":
            try:
                pygame.mixer.stop()
            except:
                pass
    
    def _validate_char(self):
        """Valide le caractère morse actuel"""
        if self.current_morse:
            if self.current_morse in REVERSE_MORSE:
                char = REVERSE_MORSE[self.current_morse]
                self.decoded_text += char
                self.char_display.config(text=char, fg=Theme.SUCCESS)
            else:
                self.char_display.config(text="?", fg=Theme.ERROR)
            
            self.text_display.config(text=self.decoded_text)
            self.current_morse = ""
            self.morse_display.config(text="")
        
        # Programmer l'ajout d'espace après une pause plus longue
        self.word_timeout_id = self.root.after(
            int(self.word_gap * 1000),
            self._add_space
        )
    
    def _add_space(self):
        """Ajoute un espace entre les mots"""
        if self.decoded_text and not self.decoded_text.endswith(" "):
            self.decoded_text += " "
            self.text_display.config(text=self.decoded_text)
    
    def _clear_keyer(self):
        """Efface tout le texte"""
        self.current_morse = ""
        self.decoded_text = ""
        self.morse_display.config(text="")
        self.char_display.config(text="?", fg=Theme.TEXT_MUTED)
        self.text_display.config(text="")

    def start_practice(self, lesson_idx):
        self.current_lesson = lesson_idx
        _, self.lesson_chars, _, _ = LESSONS[lesson_idx]
        self.score_correct = 0
        self.score_total = 0
        self.streak = 0
        self.history = []
        self.show_practice()
    
    def show_practice(self):
        """Interface d'entraînement moderne"""
        self.clear_frame()
        
        lesson_name, _, _, icon = LESSONS[self.current_lesson]
        
        # Header
        header = tk.Frame(self.main_frame, bg=Theme.BG_DARK)
        header.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        back_btn = tk.Label(
            header, text="← Retour",
            font=('Segoe UI', 11),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED,
            cursor='hand2'
        )
        back_btn.pack(side=tk.LEFT)
        back_btn.bind('<Button-1>', lambda e: self.show_menu())
        back_btn.bind('<Enter>', lambda e: back_btn.config(fg=Theme.PRIMARY))
        back_btn.bind('<Leave>', lambda e: back_btn.config(fg=Theme.TEXT_MUTED))
        
        tk.Label(
            header, text=f"{icon} {lesson_name}",
            font=('Segoe UI', 14, 'bold'),
            bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY
        ).pack(side=tk.RIGHT)
        
        # Stats cards
        stats_frame = tk.Frame(self.main_frame, bg=Theme.BG_DARK)
        stats_frame.pack(pady=15)
        
        self.score_card = StatCard(stats_frame, "SCORE", "0/0", Theme.PRIMARY)
        self.score_card.pack(side=tk.LEFT, padx=10)
        
        self.pct_card = StatCard(stats_frame, "PRÉCISION", "0%", Theme.PRIMARY)
        self.pct_card.pack(side=tk.LEFT, padx=10)
        
        self.streak_card = StatCard(stats_frame, "SÉRIE", "0", Theme.PRIMARY)
        self.streak_card.pack(side=tk.LEFT, padx=10)
        
        # Zone centrale
        center = tk.Frame(self.main_frame, bg=Theme.BG_DARK)
        center.pack(expand=True, fill=tk.BOTH, pady=10)
        
        # Orbe lumineux
        self.orb = GlowingOrb(center, size=140)
        self.orb.pack(pady=10)
        
        # Affichage du caractère
        self.display_frame = tk.Frame(center, bg=Theme.BG_DARK)
        self.display_frame.pack(pady=10)
        
        self.display_label = tk.Label(
            self.display_frame, text="?",
            font=('Segoe UI', 72, 'bold'),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED
        )
        self.display_label.pack()
        
        # Visualiseur morse
        self.morse_viz = MorseVisualizer(center, width=350, height=50)
        self.morse_viz.pack(pady=5)
        
        # Zone de saisie
        input_frame = tk.Frame(center, bg=Theme.BG_DARK)
        input_frame.pack(pady=20)
        
        self.input_entry = tk.Entry(
            input_frame,
            font=('Segoe UI', 36, 'bold'),
            width=3, justify='center',
            bg=Theme.BG_INPUT, fg=Theme.PRIMARY,
            insertbackground=Theme.PRIMARY,
            relief=tk.FLAT, highlightthickness=2,
            highlightbackground=Theme.BG_CARD,
            highlightcolor=Theme.PRIMARY
        )
        self.input_entry.pack(side=tk.LEFT, padx=10, ipady=8)
        self.input_entry.bind('<Return>', lambda e: self.check_answer())
        self.input_entry.bind('<KeyRelease>', lambda e: self.limit_input())
        
        RoundedButton(
            input_frame, "VALIDER ✓", self.check_answer,
            width=130, height=55,
            bg_color=Theme.SUCCESS,
            fg_color=Theme.BG_DARK,
            hover_color="#00cc6a",
            font_size=13
        ).pack(side=tk.LEFT, padx=10)
        
        # Boutons d'action
        action_frame = tk.Frame(center, bg=Theme.BG_DARK)
        action_frame.pack(pady=10)
        
        for text, cmd, color in [
            ("🔊 Rejouer", self.replay, Theme.PRIMARY),
            ("💡 Indice", self.show_hint, Theme.WARNING),
            ("⏭ Passer", self.skip, Theme.ERROR)
        ]:
            RoundedButton(
                action_frame, text, cmd,
                width=110, height=38,
                bg_color=Theme.BG_CARD,
                fg_color=color,
                hover_color=Theme.BG_CARD_HOVER,
                font_size=10
            ).pack(side=tk.LEFT, padx=5)
        
        # Historique visuel
        self.history_frame = tk.Frame(self.main_frame, bg=Theme.BG_DARK)
        self.history_frame.pack(fill=tk.X, padx=40, pady=10)
        
        self.next_question()
    
    def limit_input(self):
        content = self.input_entry.get()
        if len(content) > 1:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, content[-1].upper())
        elif content:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, content.upper())
    
    def next_question(self):
        self.current_char = random.choice(self.lesson_chars)
        self.display_label.config(text="?", fg=Theme.TEXT_MUTED)
        self.morse_viz.clear()
        self.input_entry.delete(0, tk.END)
        self.input_entry.focus()
        
        self.audio.set_wpm(self.wpm.get())
        self.audio.set_frequency(self.frequency.get())
        
        self.orb.set_active(True)
        self.audio.play_morse(
            self.current_char,
            callback=lambda: self.root.after(0, lambda: self.orb.set_active(False))
        )
    
    def check_answer(self):
        answer = self.input_entry.get().upper().strip()
        if not answer:
            return
        
        correct = answer == self.current_char
        self.score_total += 1
        
        if correct:
            self.score_correct += 1
            self.streak += 1
            if self.streak > self.best_streak:
                self.best_streak = self.streak
            self.display_label.config(text=self.current_char, fg=Theme.SUCCESS)
            self.morse_viz.show_morse(MORSE_CODE[self.current_char], Theme.SUCCESS)
        else:
            self.streak = 0
            self.display_label.config(text=self.current_char, fg=Theme.ERROR)
            self.morse_viz.show_morse(MORSE_CODE[self.current_char], Theme.ERROR)
        
        self.history.append((self.current_char, correct))
        self.update_display()
        
        delay = 600 if correct else 1500
        self.root.after(delay, self.next_question)
    
    def update_display(self):
        self.score_card.update_value(f"{self.score_correct}/{self.score_total}")
        
        pct = int(self.score_correct / self.score_total * 100) if self.score_total > 0 else 0
        pct_color = Theme.SUCCESS if pct >= 80 else Theme.WARNING if pct >= 60 else Theme.ERROR
        self.pct_card.update_value(f"{pct}%", pct_color)
        
        streak_text = str(self.streak)
        if self.streak >= 10:
            streak_text += " 🔥🔥"
            streak_color = Theme.SECONDARY
        elif self.streak >= 5:
            streak_text += " 🔥"
            streak_color = Theme.WARNING
        else:
            streak_color = Theme.PRIMARY
        self.streak_card.update_value(streak_text, streak_color)
        
        # Historique visuel
        for w in self.history_frame.winfo_children():
            w.destroy()
        
        for char, ok in self.history[-25:]:
            color = Theme.SUCCESS if ok else Theme.ERROR
            bg = "#1a3d2e" if ok else "#3d1a1a"
            lbl = tk.Label(
                self.history_frame, text=char,
                font=('Consolas', 10, 'bold'),
                bg=bg, fg=color,
                width=2, height=1, padx=2, pady=2
            )
            lbl.pack(side=tk.LEFT, padx=1)
    
    def replay(self):
        self.orb.set_active(True)
        self.audio.play_morse(
            self.current_char,
            callback=lambda: self.root.after(0, lambda: self.orb.set_active(False))
        )
    
    def show_hint(self):
        self.morse_viz.show_morse(MORSE_CODE[self.current_char], Theme.WARNING)
    
    def skip(self):
        self.score_total += 1
        self.streak = 0
        self.history.append((self.current_char, False))
        self.display_label.config(text=self.current_char, fg=Theme.ERROR)
        self.morse_viz.show_morse(MORSE_CODE[self.current_char], Theme.ERROR)
        self.update_display()
        self.root.after(1200, self.next_question)
    
    def show_reference(self):
        """Tableau de référence stylisé"""
        self.clear_frame()
        
        # Header
        header = tk.Frame(self.main_frame, bg=Theme.BG_DARK)
        header.pack(fill=tk.X, padx=20, pady=(15, 20))
        
        back_btn = tk.Label(
            header, text="← Retour",
            font=('Segoe UI', 11),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED,
            cursor='hand2'
        )
        back_btn.pack(side=tk.LEFT)
        back_btn.bind('<Button-1>', lambda e: self.show_menu())
        back_btn.bind('<Enter>', lambda e: back_btn.config(fg=Theme.PRIMARY))
        back_btn.bind('<Leave>', lambda e: back_btn.config(fg=Theme.TEXT_MUTED))
        
        tk.Label(
            header, text="📖 Code Morse",
            font=('Segoe UI', 18, 'bold'),
            bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY
        ).pack(side=tk.RIGHT)
        
        # Scrollable content
        canvas = tk.Canvas(self.main_frame, bg=Theme.BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=Theme.BG_DARK)
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=710)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Lettres
        tk.Label(
            scroll_frame, text="ALPHABET",
            font=('Segoe UI', 12, 'bold'),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED
        ).pack(anchor='w', padx=20, pady=(10, 10))
        
        letters_frame = tk.Frame(scroll_frame, bg=Theme.BG_DARK)
        letters_frame.pack(padx=20)
        
        for i, char in enumerate(sorted([c for c in MORSE_CODE if c.isalpha()])):
            row, col = divmod(i, 7)
            
            card = tk.Frame(letters_frame, bg=Theme.BG_CARD, padx=12, pady=10)
            card.grid(row=row, column=col, padx=4, pady=4)
            
            tk.Label(
                card, text=char,
                font=('Segoe UI', 20, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.PRIMARY
            ).pack()
            
            tk.Label(
                card, text=MORSE_CODE[char],
                font=('Consolas', 10),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
            ).pack()
            
            # Mini visualisation
            mini_viz = tk.Frame(card, bg=Theme.BG_CARD)
            mini_viz.pack(pady=(5, 0))
            for symbol in MORSE_CODE[char]:
                w = 6 if symbol == '.' else 16
                dot = tk.Frame(mini_viz, bg=Theme.PRIMARY, width=w, height=6)
                dot.pack(side=tk.LEFT, padx=1)
            
            # Click to play
            for widget in [card] + list(card.winfo_children()) + list(mini_viz.winfo_children()):
                widget.bind('<Button-1>', lambda e, c=char: self.play_ref(c))
                widget.bind('<Enter>', lambda e, c=card: self._set_card_hover(c, True))
                widget.bind('<Leave>', lambda e, c=card: self._set_card_hover(c, False))
                try:
                    widget.config(cursor='hand2')
                except:
                    pass
        
        # Chiffres
        tk.Label(
            scroll_frame, text="CHIFFRES",
            font=('Segoe UI', 12, 'bold'),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED
        ).pack(anchor='w', padx=20, pady=(20, 10))
        
        digits_frame = tk.Frame(scroll_frame, bg=Theme.BG_DARK)
        digits_frame.pack(padx=20)
        
        for i, char in enumerate("0123456789"):
            card = tk.Frame(digits_frame, bg=Theme.BG_CARD, padx=10, pady=8)
            card.grid(row=0, column=i, padx=3, pady=3)
            
            tk.Label(
                card, text=char,
                font=('Segoe UI', 18, 'bold'),
                bg=Theme.BG_CARD, fg=Theme.SUCCESS
            ).pack()
            
            tk.Label(
                card, text=MORSE_CODE[char],
                font=('Consolas', 8),
                bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED
            ).pack()
            
            for widget in [card] + list(card.winfo_children()):
                widget.bind('<Button-1>', lambda e, c=char: self.play_ref(c))
                widget.bind('<Enter>', lambda e, c=card: self._set_card_hover(c, True))
                widget.bind('<Leave>', lambda e, c=card: self._set_card_hover(c, False))
                try:
                    widget.config(cursor='hand2')
                except:
                    pass
        
        # Info
        tk.Label(
            scroll_frame,
            text="💡 Cliquez sur un caractère pour l'entendre",
            font=('Segoe UI', 10),
            bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED
        ).pack(pady=20)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    
    def _set_card_hover(self, card, hover):
        color = Theme.BG_CARD_HOVER if hover else Theme.BG_CARD
        card.config(bg=color)
        for child in card.winfo_children():
            try:
                child.config(bg=color)
                for subchild in child.winfo_children():
                    if not isinstance(subchild, tk.Frame) or subchild.cget('bg') == Theme.PRIMARY:
                        continue
                    subchild.config(bg=color)
            except:
                pass
    
    def play_ref(self, char):
        self.audio.set_wpm(self.wpm.get())
        self.audio.set_frequency(self.frequency.get())
        self.audio.play_morse(char)
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════╗
    ║      ⚡ CW TRAINER - Code Morse ⚡       ║
    ╠══════════════════════════════════════════╣
    ║  Pour l'audio:                           ║
    ║  pip install pygame numpy                ║
    ╚══════════════════════════════════════════╝
    """)
    app = MorseTrainer()
    app.run()
