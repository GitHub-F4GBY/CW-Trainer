#!/usr/bin/env python3
"""
CW Trainer - Méthode Koch
© 2025 F4GBY
"""

import subprocess, sys
for pkg in ['pygame', 'numpy']:
    try: __import__(pkg)
    except ImportError: subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import pygame
import threading
import random
import time
import json
import os
from datetime import datetime, timedelta

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

SAVE_FILE = os.path.join(os.path.expanduser("~"), "cw_trainer_progress.json")

MORSE_CODE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---',
    '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.', 
    # Ponctuation
    '.': '.-.-.-', ',': '--..--', '?': '..--..', '/': '-..-.', '=': '-...-',
    '+': '.-.-.', '-': '-....-', '@': '.--.-.', 
    # Prosigns radioamateur
    'AR': '.-.-.', 'SK': '...-.-', 'BT': '-...-', 'KN': '-.--.',
    'AS': '.-...', 'HH': '........', 'SOS': '...---...'
}

# Caractères spéciaux radioamateur (pour le mode dédié)
SPECIAL_CHARS = {
    # Ponctuation courante
    '.': ('Point', '.-.-.-'),
    ',': ('Virgule', '--..--'),
    '?': ('Question', '..--..'),
    '/': ('Barre', '-..-.'),
    '=': ('Égal/BT', '-...-'),
    '+': ('Plus/AR', '.-.-.'),
    '-': ('Tiret', '-....-'),
    '@': ('Arobase', '.--.-.'),
    # Prosigns
    'AR': ('Fin message', '.-.-.'),
    'SK': ('Fin contact', '...-.-'),
    'BT': ('Séparation', '-...-'),
    'KN': ('À vous seul', '-.--.'),
    'AS': ('Attendez', '.-...'),
    'HH': ('Erreur', '........'),
    'SOS': ('Détresse', '...---...'),
}

KOCH_ORDER = ['K', 'M', 'R', 'S', 'U', 'A', 'P', 'T', 'L', 'O', 
              'W', 'I', '.', 'N', 'J', 'E', 'F', '0', 'Y', 'V',
              ',', 'G', '5', '/', 'Q', '9', 'Z', 'H', '3', '8',
              'B', '?', '4', '2', '7', 'C', '1', 'D', '6', 'X']

CALLSIGN_PREFIXES = {
    'France': ['F1', 'F2', 'F4', 'F5', 'F6', 'F8'],
    'USA': ['K', 'W', 'N', 'AA', 'KA', 'WA'],
    'Allemagne': ['DA', 'DB', 'DL', 'DK'],
    'UK': ['G0', 'G3', 'G4', 'M0'],
    'Italie': ['I0', 'I1', 'IK', 'IZ'],
    'Espagne': ['EA', 'EB'],
    'Belgique': ['ON', 'OO'],
    'Japon': ['JA', 'JH', 'JR'],
    'Canada': ['VA', 'VE'],
}

def generate_callsign(country=None):
    if country is None: country = random.choice(list(CALLSIGN_PREFIXES.keys()))
    prefix = random.choice(CALLSIGN_PREFIXES[country])
    num = "" if prefix[-1].isdigit() else str(random.randint(1, 9))
    suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=random.randint(2, 3)))
    return f"{prefix}{num}{suffix}", country

class MorseAudio:
    def __init__(self):
        self.frequency = 650
        self.wpm = 12
        self.volume = 0.7
        self.qrm = 0  # 0-1 niveau de bruit
        self.qrm_type = "Statique"
        self.qsb = 0  # 0-1 niveau de fading
        self.qsb_speed = 0.5  # Vitesse du fading
        self.sample_rate = 44100
        self.qsb_phase = 0  # Phase du QSB pour continuité
        # Fréquences des stations QRM (générées une fois)
        self.qrm_stations = []
        self.regenerate_qrm_stations()
    
    def regenerate_qrm_stations(self):
        """Génère des stations QRM avec des fréquences différentes"""
        self.qrm_stations = [
            {'freq': self.frequency + random.randint(-200, -50), 'wpm': random.randint(12, 25)},
            {'freq': self.frequency + random.randint(50, 200), 'wpm': random.randint(10, 20)},
            {'freq': self.frequency + random.randint(-300, -150), 'wpm': random.randint(15, 30)},
        ]
    
    def generate_qsb_envelope(self, n_samples):
        """Génère une enveloppe de fading QSB"""
        if self.qsb == 0:
            return np.ones(n_samples)
        
        # Fréquence du fading (0.2 à 2 Hz selon la vitesse)
        fade_freq = 0.2 + self.qsb_speed * 1.8
        
        t = np.linspace(0, n_samples/self.sample_rate, n_samples, False)
        
        # Combinaison de plusieurs sinusoïdes pour un fading plus naturel
        fade = (
            0.5 * np.sin(2 * np.pi * fade_freq * t + self.qsb_phase) +
            0.3 * np.sin(2 * np.pi * fade_freq * 0.7 * t + self.qsb_phase * 1.3) +
            0.2 * np.sin(2 * np.pi * fade_freq * 1.3 * t + self.qsb_phase * 0.7)
        )
        
        # Normaliser entre min_level et 1
        min_level = 1 - self.qsb * 0.9  # QSB max = signal tombe à 10%
        fade = (fade + 1) / 2  # Normaliser entre 0 et 1
        fade = min_level + fade * (1 - min_level)
        
        # Mettre à jour la phase pour continuité
        self.qsb_phase += 2 * np.pi * fade_freq * n_samples / self.sample_rate
        
        return fade
        
    def generate_noise(self, n_samples):
        """Génère du bruit selon le type sélectionné"""
        if self.qrm_type == "Statique":
            # Bruit blanc classique
            noise = np.random.normal(0, 1, n_samples)
            noise = noise * self.qrm * 0.3
            
        elif self.qrm_type == "QRN":
            # Bruit atmosphérique (craquements)
            noise = np.random.normal(0, 1, n_samples)
            # Ajouter des pops aléatoires
            pops = np.random.random(n_samples) > 0.998
            noise[pops] = np.random.choice([-3, 3], size=np.sum(pops))
            # Filtrage passe-bas pour simuler l'atmosphérique
            noise = np.convolve(noise, np.ones(10)/10, mode='same')
            noise = noise * self.qrm * 0.4
            
        elif self.qrm_type == "QRM 1 Station":
            # Une station CW proche
            noise = self.generate_cw_qrm(n_samples, 1)
            
        elif self.qrm_type == "QRM 2 Stations":
            # Deux stations CW
            noise = self.generate_cw_qrm(n_samples, 2)
            
        elif self.qrm_type == "QRM Pile-up":
            # Plusieurs stations (pile-up contest)
            noise = self.generate_cw_qrm(n_samples, 3)
            
        else:
            noise = np.zeros(n_samples)
        
        return noise
    
    def generate_cw_qrm(self, n_samples, num_stations):
        """Génère du QRM avec plusieurs stations CW avec variation de tonalité"""
        noise = np.zeros(n_samples)
        t = np.linspace(0, n_samples/self.sample_rate, n_samples, False)
        
        for i in range(min(num_stations, len(self.qrm_stations))):
            station = self.qrm_stations[i]
            base_freq = station['freq']
            wpm = station['wpm']
            
            # Variation de fréquence (drift) - simule un VFO instable
            # Drift lent (0.1-0.5 Hz) avec amplitude de ±15 Hz
            drift_speed = 0.1 + random.random() * 0.4
            drift_amount = 10 + random.random() * 10  # ±10-20 Hz
            drift_phase = random.random() * 2 * np.pi
            
            # Fréquence qui varie dans le temps
            freq_variation = drift_amount * np.sin(2 * np.pi * drift_speed * t + drift_phase)
            # Ajouter un drift aléatoire supplémentaire
            freq_variation += np.cumsum(np.random.normal(0, 0.5, n_samples)) * 0.01
            
            instantaneous_freq = base_freq + freq_variation
            
            # Générer l'onde avec fréquence variable (FM synthesis)
            phase = np.cumsum(2 * np.pi * instantaneous_freq / self.sample_rate)
            wave = np.sin(phase)
            
            # Créer un pattern morse aléatoire (on/off)
            dot_samples = int(self.sample_rate * 1200 / wpm / 1000)
            envelope = np.zeros(n_samples)
            pos = 0
            
            while pos < n_samples:
                # Élément aléatoire: point ou trait
                if random.random() > 0.5:
                    dur = dot_samples
                else:
                    dur = dot_samples * 3
                
                # Attack/decay pour éviter les clics
                if pos + dur < n_samples:
                    attack = min(int(0.003 * self.sample_rate), dur // 4)
                    envelope[pos:pos+attack] = np.linspace(0, 1, attack)
                    envelope[pos+attack:pos+dur-attack] = 1
                    envelope[pos+dur-attack:pos+dur] = np.linspace(1, 0, attack)
                
                pos += dur
                
                # Espace entre éléments
                gap = dot_samples * random.choice([1, 3, 7])
                pos += gap
            
            # Volume variable pour chaque station (simule distances différentes)
            station_volume = 0.2 + random.random() * 0.3
            
            # Ajouter cette station au bruit
            noise += wave * envelope * station_volume
        
        # Normaliser et appliquer le niveau QRM
        noise = noise * self.qrm * 0.5
        
        return noise
        
    def play(self, text):
        # Régénérer les stations QRM pour varier
        if self.qrm > 0 and "QRM" in self.qrm_type:
            self.regenerate_qrm_stations()
        
        # Reset QSB phase au début de chaque transmission
        self.qsb_phase = random.random() * 2 * np.pi
            
        dot = 1200 / self.wpm
        for char in text.upper():
            morse = MORSE_CODE.get(char, '')
            if not morse: continue
            for i, sym in enumerate(morse):
                dur = dot if sym == '.' else dot * 3
                n = int(self.sample_rate * dur / 1000)
                t = np.linspace(0, dur/1000, n, False)
                wave = np.sin(2 * np.pi * self.frequency * t)
                att = min(int(0.005 * self.sample_rate), n//2)
                envelope = np.ones(n)
                envelope[:att] = np.linspace(0, 1, att)
                envelope[-att:] = np.linspace(1, 0, att)
                
                # Appliquer le QSB (fading)
                qsb_envelope = self.generate_qsb_envelope(n)
                wave = wave * envelope * self.volume * qsb_envelope
                
                # Ajouter le bruit QRM
                if self.qrm > 0:
                    noise = self.generate_noise(n)
                    wave = wave + noise
                    # Normaliser pour éviter la saturation
                    max_val = np.max(np.abs(wave))
                    if max_val > 1:
                        wave = wave / max_val
                
                wave = (wave * 32767).astype(np.int16)
                sound = pygame.sndarray.make_sound(np.column_stack((wave, wave)))
                sound.play()
                time.sleep(dur / 1000)
                
                # Bruit entre les éléments
                if i < len(morse) - 1:
                    if self.qrm > 0:
                        gap_n = int(self.sample_rate * dot / 1000)
                        gap_noise = self.generate_noise(gap_n)
                        gap_noise = (gap_noise * 32767).astype(np.int16)
                        gap_sound = pygame.sndarray.make_sound(np.column_stack((gap_noise, gap_noise)))
                        gap_sound.play()
                    time.sleep(dot / 1000)
            
            # Bruit entre les caractères
            if self.qrm > 0:
                gap_n = int(self.sample_rate * dot * 3 / 1000)
                gap_noise = self.generate_noise(gap_n)
                gap_noise = (gap_noise * 32767).astype(np.int16)
                gap_sound = pygame.sndarray.make_sound(np.column_stack((gap_noise, gap_noise)))
                gap_sound.play()
            time.sleep(dot * 3 / 1000)

class App:
    BG = '#0d1117'
    BG2 = '#161b22'
    BG3 = '#21262d'
    CYAN = '#58a6ff'
    GREEN = '#3fb950'
    ORANGE = '#d29922'
    RED = '#f85149'
    PURPLE = '#a371f7'
    TEXT = '#c9d1d9'
    DIM = '#8b949e'
    
    def __init__(self, root):
        self.root = root
        self.root.title("CW Trainer - F4GBY - Méthode Koch")
        self.root.geometry("1050x700")
        self.root.configure(bg=self.BG)
        
        self.audio = MorseAudio()
        self.mode = 'koch'
        
        # Koch
        self.koch_level = 2
        self.koch_char = ''
        self.koch_correct = 0
        self.koch_total = 0
        self.koch_running = False
        self.koch_start_time = None
        self.koch_duration = 5
        
        # Stats par caractère
        self.char_stats = {}
        self.history = []
        
        # Indicatifs
        self.call_current = ''
        self.call_country = ''
        self.call_correct = 0
        self.call_total = 0
        self.call_running = False
        self.call_start_time = None
        self.call_duration = 5
        
        # Contest
        self.contest_on = False
        self.contest_call = ''
        self.contest_country = ''
        self.contest_qsos = 0
        self.contest_duration = 5
        
        # Spéciaux
        self.special_char = ''
        self.special_correct = 0
        self.special_total = 0
        self.special_running = False
        self.special_start_time = None
        self.special_duration = 5
        
        self.load_progress()
        self.build()
        
    def save_progress(self):
        data = {'koch_level': self.koch_level, 'history': self.history[-50:], 'char_stats': self.char_stats}
        try:
            with open(SAVE_FILE, 'w') as f: json.dump(data, f)
        except: pass
    
    def load_progress(self):
        try:
            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, 'r') as f:
                    data = json.load(f)
                    self.koch_level = data.get('koch_level', 2)
                    self.history = data.get('history', [])
                    self.char_stats = data.get('char_stats', {})
        except: pass
    
    def reset_progress(self):
        if messagebox.askyesno("Reset", "Tout recommencer à zéro ?"):
            self.koch_level = 2
            self.koch_correct = 0
            self.koch_total = 0
            self.history = []
            self.char_stats = {}
            self.save_progress()
            self.set_mode('koch')
    
    def add_session(self, correct, total):
        if total > 0:
            self.history.append({
                'date': datetime.now().strftime("%d/%m %H:%M"),
                'level': self.koch_level,
                'correct': correct,
                'total': total,
                'pct': round(correct / total * 100)
            })
            self.save_progress()
    
    def build(self):
        # ═══════════════════════════════════════════════════════════
        # SIDEBAR GAUCHE
        # ═══════════════════════════════════════════════════════════
        sidebar = tk.Frame(self.root, bg=self.BG2, width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        # Titre
        tk.Label(sidebar, text="⚡ CW TRAINER", font=('Arial', 14, 'bold'), 
                fg=self.CYAN, bg=self.BG2).pack(pady=20)
        
        # Modes
        tk.Label(sidebar, text="MODE", font=('Arial', 9), fg=self.DIM, bg=self.BG2).pack(pady=(10,5))
        
        self.btn_koch = tk.Button(sidebar, text="📚 Koch", font=('Arial', 11), width=15,
                                 relief=tk.FLAT, cursor='hand2', command=lambda: self.set_mode('koch'))
        self.btn_koch.pack(pady=2)
        
        self.btn_special = tk.Button(sidebar, text="📡 Spéciaux", font=('Arial', 11), width=15,
                                    relief=tk.FLAT, cursor='hand2', command=lambda: self.set_mode('special'))
        self.btn_special.pack(pady=2)
        
        self.btn_call = tk.Button(sidebar, text="📻 Indicatifs", font=('Arial', 11), width=15,
                                 relief=tk.FLAT, cursor='hand2', command=lambda: self.set_mode('call'))
        self.btn_call.pack(pady=2)
        
        self.btn_contest = tk.Button(sidebar, text="🏆 Contest", font=('Arial', 11), width=15,
                                    relief=tk.FLAT, cursor='hand2', command=lambda: self.set_mode('contest'))
        self.btn_contest.pack(pady=2)
        
        # Séparateur
        tk.Frame(sidebar, bg=self.DIM, height=1).pack(fill=tk.X, padx=15, pady=20)
        
        # Réglages audio
        tk.Label(sidebar, text="AUDIO", font=('Arial', 9), fg=self.DIM, bg=self.BG2).pack(pady=(0,10))
        
        # Vitesse
        tk.Label(sidebar, text="Vitesse (WPM)", font=('Arial', 9), fg=self.TEXT, bg=self.BG2).pack()
        self.wpm_scale = tk.Scale(sidebar, from_=5, to=35, orient=tk.HORIZONTAL, 
                                 bg=self.BG2, fg=self.TEXT, highlightthickness=0, length=150,
                                 command=lambda v: setattr(self.audio, 'wpm', int(v)))
        self.wpm_scale.set(12)
        self.wpm_scale.pack()
        
        # Tonalité
        tk.Label(sidebar, text="Tonalité (Hz)", font=('Arial', 9), fg=self.TEXT, bg=self.BG2).pack(pady=(10,0))
        self.freq_scale = tk.Scale(sidebar, from_=400, to=900, orient=tk.HORIZONTAL, 
                                  bg=self.BG2, fg=self.TEXT, highlightthickness=0, length=150,
                                  command=lambda v: setattr(self.audio, 'frequency', int(v)))
        self.freq_scale.set(650)
        self.freq_scale.pack()
        
        # Volume
        tk.Label(sidebar, text="Volume", font=('Arial', 9), fg=self.TEXT, bg=self.BG2).pack(pady=(10,0))
        self.vol_scale = tk.Scale(sidebar, from_=0, to=100, orient=tk.HORIZONTAL, 
                                 bg=self.BG2, fg=self.TEXT, highlightthickness=0, length=150,
                                 command=lambda v: setattr(self.audio, 'volume', int(v)/100))
        self.vol_scale.set(70)
        self.vol_scale.pack()
        
        # Séparateur
        tk.Frame(sidebar, bg=self.DIM, height=1).pack(fill=tk.X, padx=15, pady=15)
        
        # QRM (bruit)
        tk.Label(sidebar, text="QRM (Bruit)", font=('Arial', 9), fg=self.TEXT, bg=self.BG2).pack()
        self.qrm_scale = tk.Scale(sidebar, from_=0, to=100, orient=tk.HORIZONTAL, 
                                 bg=self.BG2, fg=self.TEXT, highlightthickness=0, length=150,
                                 command=lambda v: setattr(self.audio, 'qrm', int(v)/100))
        self.qrm_scale.set(0)
        self.qrm_scale.pack()
        
        # Type de QRM
        tk.Label(sidebar, text="Type QRM", font=('Arial', 9), fg=self.TEXT, bg=self.BG2).pack(pady=(10,0))
        self.qrm_type = ttk.Combobox(sidebar, values=[
            "Statique", 
            "QRN", 
            "QRM 1 Station",
            "QRM 2 Stations", 
            "QRM Pile-up"
        ], state='readonly', width=14)
        self.qrm_type.set("Statique")
        self.qrm_type.pack(pady=5)
        self.qrm_type.bind('<<ComboboxSelected>>', lambda e: setattr(self.audio, 'qrm_type', self.qrm_type.get()))
        
        # Séparateur
        tk.Frame(sidebar, bg=self.DIM, height=1).pack(fill=tk.X, padx=15, pady=10)
        
        # QSB (fading)
        tk.Label(sidebar, text="QSB (Fading)", font=('Arial', 9), fg=self.TEXT, bg=self.BG2).pack()
        self.qsb_scale = tk.Scale(sidebar, from_=0, to=100, orient=tk.HORIZONTAL, 
                                 bg=self.BG2, fg=self.TEXT, highlightthickness=0, length=150,
                                 command=lambda v: setattr(self.audio, 'qsb', int(v)/100))
        self.qsb_scale.set(0)
        self.qsb_scale.pack()
        
        # Vitesse QSB
        tk.Label(sidebar, text="Vitesse QSB", font=('Arial', 9), fg=self.TEXT, bg=self.BG2).pack(pady=(5,0))
        self.qsb_speed_scale = tk.Scale(sidebar, from_=0, to=100, orient=tk.HORIZONTAL, 
                                       bg=self.BG2, fg=self.TEXT, highlightthickness=0, length=150,
                                       command=lambda v: setattr(self.audio, 'qsb_speed', int(v)/100))
        self.qsb_speed_scale.set(50)
        self.qsb_speed_scale.pack()
        
        # Footer
        tk.Label(sidebar, text="© 2025 F4GBY", font=('Arial', 8), 
                fg=self.DIM, bg=self.BG2).pack(side=tk.BOTTOM, pady=10)
        
        # ═══════════════════════════════════════════════════════════
        # CONTENT
        # ═══════════════════════════════════════════════════════════
        self.content = tk.Frame(self.root, bg=self.BG)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.set_mode('koch')
    
    def set_mode(self, mode):
        self.mode = mode
        self.koch_running = False
        self.call_running = False
        self.contest_on = False
        self.special_running = False
        
        self.btn_koch.config(bg=self.CYAN if mode=='koch' else self.BG3, 
                            fg=self.BG if mode=='koch' else self.CYAN)
        self.btn_special.config(bg=self.GREEN if mode=='special' else self.BG3, 
                               fg=self.BG if mode=='special' else self.GREEN)
        self.btn_call.config(bg=self.PURPLE if mode=='call' else self.BG3, 
                            fg=self.BG if mode=='call' else self.PURPLE)
        self.btn_contest.config(bg=self.ORANGE if mode=='contest' else self.BG3, 
                               fg=self.BG if mode=='contest' else self.ORANGE)
        
        for w in self.content.winfo_children(): w.destroy()
        
        if mode == 'koch': self.show_koch()
        elif mode == 'special': self.show_special()
        elif mode == 'call': self.show_call()
        else: self.show_contest()
    
    def play(self, txt):
        threading.Thread(target=lambda: self.audio.play(txt), daemon=True).start()

    # ════════════════════════════════════════════════════════════════
    # MÉTHODE KOCH
    # ════════════════════════════════════════════════════════════════
    
    def show_koch(self):
        main = tk.Frame(self.content, bg=self.BG)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # LEFT
        left = tk.Frame(main, bg=self.BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        chars = KOCH_ORDER[:self.koch_level]
        
        # Header
        hdr = tk.Frame(left, bg=self.BG)
        hdr.pack(fill=tk.X, pady=(0,10))
        tk.Label(hdr, text=f"📚 Méthode Koch - Niveau {self.koch_level}/{len(KOCH_ORDER)}", 
                font=('Arial', 14, 'bold'), fg=self.CYAN, bg=self.BG).pack(side=tk.LEFT)
        tk.Button(hdr, text="🔄 Reset", font=('Arial', 9), fg=self.RED, bg=self.BG3,
                 relief=tk.FLAT, command=self.reset_progress).pack(side=tk.RIGHT)
        
        # Mode : Koch ou Personnalisé
        mode_f = tk.Frame(left, bg=self.BG)
        mode_f.pack(pady=5)
        
        self.koch_mode_var = tk.StringVar(value="koch")
        tk.Radiobutton(mode_f, text="Méthode Koch", variable=self.koch_mode_var, value="koch",
                      font=('Arial', 10), fg=self.TEXT, bg=self.BG, selectcolor=self.BG3,
                      activebackground=self.BG, command=self.update_koch_mode).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(mode_f, text="Personnalisé", variable=self.koch_mode_var, value="custom",
                      font=('Arial', 10), fg=self.TEXT, bg=self.BG, selectcolor=self.BG3,
                      activebackground=self.BG, command=self.update_koch_mode).pack(side=tk.LEFT, padx=10)
        
        # Frame pour les caractères Koch
        self.koch_chars_frame = tk.Frame(left, bg=self.BG)
        self.koch_chars_frame.pack(pady=5)
        
        # Caractères Koch
        for c in chars:
            lbl = tk.Label(self.koch_chars_frame, text=f" {c} ", font=('Consolas', 11, 'bold'), 
                          fg=self.CYAN, bg=self.BG3, cursor='hand2')
            lbl.pack(side=tk.LEFT, padx=1)
            lbl.bind('<Button-1>', lambda e, ch=c: self.play(ch))
        
        if self.koch_level > 2:
            new = KOCH_ORDER[self.koch_level - 1]
            self.koch_new_lbl = tk.Label(left, text=f"✨ Nouveau : {new} = {MORSE_CODE[new]}", 
                    font=('Arial', 11, 'bold'), fg=self.GREEN, bg=self.BG)
            self.koch_new_lbl.pack(pady=5)
        else:
            self.koch_new_lbl = None
        
        # Frame pour personnalisé (caché par défaut)
        self.custom_frame = tk.Frame(left, bg=self.BG)
        
        tk.Label(self.custom_frame, text="Entrez vos caractères :", font=('Arial', 10), 
                fg=self.TEXT, bg=self.BG).pack()
        
        self.custom_entry = tk.Entry(self.custom_frame, font=('Consolas', 14), width=25, 
                                    justify=tk.CENTER, bg=self.BG3, fg=self.CYAN, insertbackground=self.CYAN)
        self.custom_entry.pack(pady=5)
        self.custom_entry.insert(0, "KMRSU")
        
        tk.Label(self.custom_frame, text="(lettres, chiffres, . , ? /)", font=('Arial', 9), 
                fg=self.DIM, bg=self.BG).pack()
        
        # Durée
        dur_f = tk.Frame(left, bg=self.BG)
        dur_f.pack(pady=10)
        tk.Label(dur_f, text="Durée :", font=('Arial', 10), fg=self.TEXT, bg=self.BG).pack(side=tk.LEFT)
        self.koch_dur_combo = ttk.Combobox(dur_f, values=["2", "5", "10", "15", "∞"], width=5, state='readonly')
        self.koch_dur_combo.set("5")
        self.koch_dur_combo.pack(side=tk.LEFT, padx=5)
        tk.Label(dur_f, text="min", font=('Arial', 10), fg=self.DIM, bg=self.BG).pack(side=tk.LEFT)
        
        # Timer et stats
        stats_f = tk.Frame(left, bg=self.BG)
        stats_f.pack(pady=5)
        self.koch_timer_lbl = tk.Label(stats_f, text="⏱ --:--", font=('Arial', 12), fg=self.ORANGE, bg=self.BG)
        self.koch_timer_lbl.pack(side=tk.LEFT, padx=15)
        self.koch_stats_lbl = tk.Label(stats_f, text="0/0 (0%)", font=('Arial', 12), fg=self.TEXT, bg=self.BG)
        self.koch_stats_lbl.pack(side=tk.LEFT, padx=15)
        
        tk.Label(left, text="🎯 90% sur 10 essais = niveau suivant", 
                font=('Arial', 9), fg=self.DIM, bg=self.BG).pack()
        
        # Display
        self.koch_display = tk.Label(left, text="?", font=('Consolas', 64, 'bold'), fg=self.DIM, bg=self.BG)
        self.koch_display.pack(pady=15)
        
        # Entry
        self.koch_entry = tk.Entry(left, font=('Consolas', 28), width=5, justify=tk.CENTER,
                                  bg=self.BG3, fg=self.CYAN, insertbackground=self.CYAN)
        self.koch_entry.pack(pady=5)
        self.koch_entry.bind('<Return>', lambda e: self.koch_enter())
        
        # Feedback
        self.koch_feedback = tk.Label(left, text="Appuyez sur Démarrer", font=('Arial', 11), fg=self.DIM, bg=self.BG)
        self.koch_feedback.pack(pady=5)
        
        # Boutons
        btns = tk.Frame(left, bg=self.BG)
        btns.pack(pady=10)
        self.koch_btn = tk.Button(btns, text="▶ Démarrer", font=('Arial', 11), 
                                 fg='white', bg=self.GREEN, relief=tk.FLAT, padx=20, pady=8,
                                 command=self.koch_start)
        self.koch_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="🔄 Rejouer", font=('Arial', 11), 
                 fg='white', bg=self.ORANGE, relief=tk.FLAT, padx=20, pady=8,
                 command=lambda: self.play(self.koch_char) if self.koch_char else None).pack(side=tk.LEFT, padx=5)
        self.koch_stop_btn = tk.Button(btns, text="⏹ Stop", font=('Arial', 11), 
                                      fg='white', bg=self.RED, relief=tk.FLAT, padx=20, pady=8,
                                      command=self.koch_stop, state=tk.DISABLED)
        self.koch_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # RIGHT - Stats
        right = tk.Frame(main, bg=self.BG2, width=200)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(20,0))
        right.pack_propagate(False)
        
        tk.Label(right, text="📊 Stats", font=('Arial', 11, 'bold'), fg=self.TEXT, bg=self.BG2).pack(pady=10)
        
        # Tableau
        hdr_f = tk.Frame(right, bg=self.BG3)
        hdr_f.pack(fill=tk.X, padx=10)
        tk.Label(hdr_f, text="Car", font=('Consolas', 9, 'bold'), fg=self.DIM, bg=self.BG3, width=4).pack(side=tk.LEFT)
        tk.Label(hdr_f, text="OK", font=('Consolas', 9, 'bold'), fg=self.GREEN, bg=self.BG3, width=4).pack(side=tk.LEFT)
        tk.Label(hdr_f, text="Err", font=('Consolas', 9, 'bold'), fg=self.RED, bg=self.BG3, width=4).pack(side=tk.LEFT)
        tk.Label(hdr_f, text="%", font=('Consolas', 9, 'bold'), fg=self.CYAN, bg=self.BG3, width=5).pack(side=tk.LEFT)
        
        # Canvas scrollable
        canvas = tk.Canvas(right, bg=self.BG2, highlightthickness=0, width=180)
        scrollbar = tk.Scrollbar(right, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.BG2)
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        for char in chars:
            stats = self.char_stats.get(char, [0, 0])
            correct, total = stats[0], stats[1]
            errors = total - correct
            pct = (correct / total * 100) if total > 0 else 0
            
            color = self.DIM if total == 0 else self.GREEN if pct >= 90 else self.ORANGE if pct >= 70 else self.RED
            
            row = tk.Frame(scroll_frame, bg=self.BG2)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=char, font=('Consolas', 10, 'bold'), fg=self.CYAN, bg=self.BG2, width=4).pack(side=tk.LEFT)
            tk.Label(row, text=str(correct), font=('Consolas', 10), fg=self.GREEN, bg=self.BG2, width=4).pack(side=tk.LEFT)
            tk.Label(row, text=str(errors), font=('Consolas', 10), fg=self.RED, bg=self.BG2, width=4).pack(side=tk.LEFT)
            tk.Label(row, text=f"{pct:.0f}%" if total > 0 else "-", font=('Consolas', 10), fg=color, bg=self.BG2, width=5).pack(side=tk.LEFT)
        
        # Global
        tk.Frame(right, bg=self.DIM, height=1).pack(fill=tk.X, padx=10, pady=10)
        total_ok = sum(s[0] for s in self.char_stats.values())
        total_all = sum(s[1] for s in self.char_stats.values())
        gpct = (total_ok / total_all * 100) if total_all > 0 else 0
        tk.Label(right, text=f"Global: {total_ok}/{total_all} ({gpct:.0f}%)", 
                font=('Consolas', 10, 'bold'), fg=self.CYAN, bg=self.BG2).pack()
    
    def koch_start(self):
        dur = self.koch_dur_combo.get()
        self.koch_duration = 9999 if dur == "∞" else int(dur)
        self.koch_start_time = datetime.now()
        self.koch_running = True
        self.koch_correct = 0
        self.koch_total = 0
        self.koch_btn.config(state=tk.DISABLED)
        self.koch_stop_btn.config(state=tk.NORMAL)
        self.update_koch_timer()
        self.koch_next()
    
    def koch_stop(self):
        self.koch_running = False
        self.koch_btn.config(state=tk.NORMAL, text="▶ Démarrer")
        self.koch_stop_btn.config(state=tk.DISABLED)
        if self.koch_total > 0:
            self.add_session(self.koch_correct, self.koch_total)
        self.koch_feedback.config(text="Entraînement terminé", fg=self.ORANGE)
    
    def update_koch_timer(self):
        if not self.koch_running: return
        elapsed = datetime.now() - self.koch_start_time
        remain = timedelta(minutes=self.koch_duration) - elapsed
        if remain.total_seconds() <= 0:
            self.koch_stop()
            return
        m, s = int(remain.total_seconds() // 60), int(remain.total_seconds() % 60)
        if self.koch_duration < 9999:
            self.koch_timer_lbl.config(text=f"⏱ {m}:{s:02d}", fg=self.RED if remain.total_seconds() < 60 else self.ORANGE)
        else:
            elapsed_m = int(elapsed.total_seconds() // 60)
            elapsed_s = int(elapsed.total_seconds() % 60)
            self.koch_timer_lbl.config(text=f"⏱ {elapsed_m}:{elapsed_s:02d}", fg=self.ORANGE)
        self.root.after(1000, self.update_koch_timer)
    
    def koch_enter(self):
        if not self.koch_running:
            self.koch_start()
        elif self.koch_char:
            ans = self.koch_entry.get().strip().upper()
            if ans:
                self.koch_check()
                self.root.after(600, self.koch_next)
            else:
                self.koch_next()
    
    def koch_next(self):
        if not self.koch_running: return
        chars = self.get_practice_chars()
        
        # Pondération du nouveau caractère uniquement en mode Koch
        if self.koch_mode_var.get() == "koch" and self.koch_level > 2:
            new = KOCH_ORDER[self.koch_level - 1]
            pool = chars + [new] * 2
        else:
            pool = chars
        
        self.koch_char = random.choice(pool)
        self.koch_entry.delete(0, tk.END)
        self.koch_display.config(text="?", fg=self.ORANGE)
        self.koch_feedback.config(text="Écoutez...", fg=self.DIM)
        self.play(self.koch_char)
        self.koch_entry.focus()
    
    def koch_check(self):
        if not self.koch_char: return
        ans = self.koch_entry.get().strip().upper()
        if not ans: return
        
        self.koch_total += 1
        if self.koch_char not in self.char_stats:
            self.char_stats[self.koch_char] = [0, 0]
        self.char_stats[self.koch_char][1] += 1
        
        if ans == self.koch_char:
            self.koch_correct += 1
            self.char_stats[self.koch_char][0] += 1
            self.koch_display.config(text=self.koch_char, fg=self.GREEN)
            self.koch_feedback.config(text=f"✓ {MORSE_CODE[self.koch_char]}", fg=self.GREEN)
        else:
            self.koch_display.config(text=self.koch_char, fg=self.RED)
            self.koch_feedback.config(text=f"✗ C'était {self.koch_char} ({MORSE_CODE[self.koch_char]})", fg=self.RED)
        
        pct = (self.koch_correct / self.koch_total * 100) if self.koch_total > 0 else 0
        self.koch_stats_lbl.config(text=f"{self.koch_correct}/{self.koch_total} ({pct:.0f}%)")
        self.save_progress()
        
        # Proposition de passer au niveau suivant (mode Koch uniquement)
        if self.koch_mode_var.get() == "koch":
            if self.koch_total >= 10 and pct >= 90 and self.koch_level < len(KOCH_ORDER):
                self.koch_running = False
                self.koch_btn.config(state=tk.NORMAL)
                self.koch_stop_btn.config(state=tk.DISABLED)
                new = KOCH_ORDER[self.koch_level]
                self.add_session(self.koch_correct, self.koch_total)
                
                # Demander confirmation
                if messagebox.askyesno("Niveau suivant", 
                    f"Bravo ! {pct:.0f}% de réussite !\n\n"
                    f"Voulez-vous passer au niveau {self.koch_level + 1} ?\n"
                    f"Nouveau caractère : {new} ({MORSE_CODE[new]})"):
                    self.koch_level += 1
                    self.save_progress()
                
                self.koch_correct = 0
                self.koch_total = 0
                self.set_mode('koch')
    
    def update_koch_mode(self):
        """Bascule entre mode Koch et personnalisé"""
        if self.koch_mode_var.get() == "koch":
            self.custom_frame.pack_forget()
            self.koch_chars_frame.pack(pady=5)
            if self.koch_new_lbl:
                self.koch_new_lbl.pack(pady=5)
        else:
            self.koch_chars_frame.pack_forget()
            if self.koch_new_lbl:
                self.koch_new_lbl.pack_forget()
            self.custom_frame.pack(pady=10)
    
    def get_practice_chars(self):
        """Retourne les caractères à pratiquer selon le mode"""
        if self.koch_mode_var.get() == "custom":
            custom = self.custom_entry.get().upper()
            chars = [c for c in custom if c in MORSE_CODE]
            return chars if chars else ['K', 'M']
        else:
            return KOCH_ORDER[:self.koch_level]

    # ════════════════════════════════════════════════════════════════
    # CARACTÈRES SPÉCIAUX
    # ════════════════════════════════════════════════════════════════
    
    def show_special(self):
        self.special_correct = 0
        self.special_total = 0
        
        main = tk.Frame(self.content, bg=self.BG)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main, text="📡 Caractères Spéciaux Radioamateur", font=('Arial', 14, 'bold'), 
                fg=self.GREEN, bg=self.BG).pack(pady=(0,15))
        
        # Tableau de référence
        ref_frame = tk.Frame(main, bg=self.BG2)
        ref_frame.pack(pady=10, fill=tk.X)
        
        tk.Label(ref_frame, text="📖 Référence (cliquez pour écouter)", font=('Arial', 10, 'bold'), 
                fg=self.TEXT, bg=self.BG2).pack(pady=5)
        
        # Ponctuation
        punct_frame = tk.Frame(ref_frame, bg=self.BG2)
        punct_frame.pack(pady=5)
        tk.Label(punct_frame, text="Ponctuation:", font=('Arial', 9), fg=self.DIM, bg=self.BG2).pack(side=tk.LEFT, padx=5)
        
        for char in ['.', ',', '?', '/', '=', '+', '-', '@']:
            name, morse = SPECIAL_CHARS[char]
            btn = tk.Label(punct_frame, text=f" {char} ", font=('Consolas', 12, 'bold'), 
                          fg=self.CYAN, bg=self.BG3, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind('<Button-1>', lambda e, c=char: self.play_special(c))
        
        # Prosigns
        pro_frame = tk.Frame(ref_frame, bg=self.BG2)
        pro_frame.pack(pady=5)
        tk.Label(pro_frame, text="Prosigns:", font=('Arial', 9), fg=self.DIM, bg=self.BG2).pack(side=tk.LEFT, padx=5)
        
        for char in ['AR', 'SK', 'BT', 'KN', 'AS', 'HH', 'SOS']:
            name, morse = SPECIAL_CHARS[char]
            btn = tk.Label(pro_frame, text=f" {char} ", font=('Consolas', 12, 'bold'), 
                          fg=self.ORANGE, bg=self.BG3, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind('<Button-1>', lambda e, c=char: self.play_special(c))
        
        # Sélection des caractères à pratiquer
        select_frame = tk.Frame(main, bg=self.BG)
        select_frame.pack(pady=10)
        
        tk.Label(select_frame, text="Pratiquer :", font=('Arial', 10), fg=self.TEXT, bg=self.BG).pack(side=tk.LEFT)
        self.special_combo = ttk.Combobox(select_frame, values=[
            "Tous", "Ponctuation", "Prosigns"
        ], state='readonly', width=15)
        self.special_combo.set("Tous")
        self.special_combo.pack(side=tk.LEFT, padx=10)
        
        tk.Label(select_frame, text="Durée :", font=('Arial', 10), fg=self.TEXT, bg=self.BG).pack(side=tk.LEFT, padx=(20,0))
        self.special_dur_combo = ttk.Combobox(select_frame, values=["2", "5", "10", "15", "∞"], width=5, state='readonly')
        self.special_dur_combo.set("5")
        self.special_dur_combo.pack(side=tk.LEFT, padx=5)
        tk.Label(select_frame, text="min", font=('Arial', 10), fg=self.DIM, bg=self.BG).pack(side=tk.LEFT)
        
        # Stats
        stats_f = tk.Frame(main, bg=self.BG)
        stats_f.pack(pady=10)
        self.special_timer_lbl = tk.Label(stats_f, text="⏱ --:--", font=('Arial', 12), fg=self.ORANGE, bg=self.BG)
        self.special_timer_lbl.pack(side=tk.LEFT, padx=15)
        self.special_stats_lbl = tk.Label(stats_f, text="Score: 0/0", font=('Arial', 12), fg=self.TEXT, bg=self.BG)
        self.special_stats_lbl.pack(side=tk.LEFT, padx=15)
        
        # Display
        self.special_display = tk.Label(main, text="?", font=('Consolas', 48, 'bold'), fg=self.DIM, bg=self.BG)
        self.special_display.pack(pady=10)
        
        self.special_name_lbl = tk.Label(main, text="", font=('Arial', 10), fg=self.GREEN, bg=self.BG)
        self.special_name_lbl.pack()
        
        # Entry
        self.special_entry = tk.Entry(main, font=('Consolas', 24), width=8, justify=tk.CENTER,
                                     bg=self.BG3, fg=self.GREEN, insertbackground=self.GREEN)
        self.special_entry.pack(pady=10)
        self.special_entry.bind('<Return>', lambda e: self.special_enter())
        
        # Feedback
        self.special_feedback = tk.Label(main, text="Appuyez sur Démarrer", font=('Arial', 11), fg=self.DIM, bg=self.BG)
        self.special_feedback.pack(pady=5)
        
        # Boutons
        btns = tk.Frame(main, bg=self.BG)
        btns.pack(pady=10)
        self.special_btn = tk.Button(btns, text="▶ Démarrer", font=('Arial', 11), 
                                    fg='white', bg=self.GREEN, relief=tk.FLAT, padx=20, pady=8,
                                    command=self.special_start)
        self.special_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="🔄 Rejouer", font=('Arial', 11), 
                 fg='white', bg=self.ORANGE, relief=tk.FLAT, padx=20, pady=8,
                 command=lambda: self.play_special(self.special_char) if self.special_char else None).pack(side=tk.LEFT, padx=5)
        self.special_stop_btn = tk.Button(btns, text="⏹ Stop", font=('Arial', 11), 
                                         fg='white', bg=self.RED, relief=tk.FLAT, padx=20, pady=8,
                                         command=self.special_stop, state=tk.DISABLED)
        self.special_stop_btn.pack(side=tk.LEFT, padx=5)
    
    def play_special(self, char):
        """Joue un caractère spécial"""
        if char in SPECIAL_CHARS:
            name, morse = SPECIAL_CHARS[char]
            # Jouer le morse directement
            threading.Thread(target=lambda: self.play_morse_direct(morse), daemon=True).start()
    
    def play_morse_direct(self, morse):
        """Joue directement un code morse"""
        dot = 1200 / self.audio.wpm
        for sym in morse:
            if sym == '.':
                dur = dot
            elif sym == '-':
                dur = dot * 3
            else:
                continue
            n = int(44100 * dur / 1000)
            t = np.linspace(0, dur/1000, n, False)
            wave = np.sin(2 * np.pi * self.audio.frequency * t)
            att = min(int(0.005 * 44100), n//2)
            envelope = np.ones(n)
            envelope[:att] = np.linspace(0, 1, att)
            envelope[-att:] = np.linspace(1, 0, att)
            wave = wave * envelope * self.audio.volume
            
            # Ajouter le bruit QRM
            if self.audio.qrm > 0:
                noise = self.audio.generate_noise(n)
                wave = wave + noise
                max_val = np.max(np.abs(wave))
                if max_val > 1:
                    wave = wave / max_val
            
            wave = (wave * 32767).astype(np.int16)
            sound = pygame.sndarray.make_sound(np.column_stack((wave, wave)))
            sound.play()
            time.sleep(dur / 1000)
            time.sleep(dot / 1000)
    
    def get_special_chars(self):
        """Retourne les caractères spéciaux selon la sélection"""
        mode = self.special_combo.get()
        if mode == "Ponctuation":
            return ['.', ',', '?', '/', '=', '+', '-', '@']
        elif mode == "Prosigns":
            return ['AR', 'SK', 'BT', 'KN', 'AS', 'HH', 'SOS']
        else:
            return list(SPECIAL_CHARS.keys())
    
    def special_start(self):
        dur = self.special_dur_combo.get()
        self.special_duration = 9999 if dur == "∞" else int(dur)
        self.special_start_time = datetime.now()
        self.special_running = True
        self.special_correct = 0
        self.special_total = 0
        self.special_btn.config(state=tk.DISABLED)
        self.special_stop_btn.config(state=tk.NORMAL)
        self.update_special_timer()
        self.special_next()
    
    def special_stop(self):
        self.special_running = False
        self.special_btn.config(state=tk.NORMAL)
        self.special_stop_btn.config(state=tk.DISABLED)
        self.special_feedback.config(text="Entraînement terminé", fg=self.ORANGE)
    
    def update_special_timer(self):
        if not self.special_running: return
        elapsed = datetime.now() - self.special_start_time
        remain = timedelta(minutes=self.special_duration) - elapsed
        if remain.total_seconds() <= 0:
            self.special_stop()
            return
        m, s = int(remain.total_seconds() // 60), int(remain.total_seconds() % 60)
        if self.special_duration < 9999:
            self.special_timer_lbl.config(text=f"⏱ {m}:{s:02d}", fg=self.RED if remain.total_seconds() < 60 else self.ORANGE)
        else:
            em, es = int(elapsed.total_seconds() // 60), int(elapsed.total_seconds() % 60)
            self.special_timer_lbl.config(text=f"⏱ {em}:{es:02d}", fg=self.ORANGE)
        self.root.after(1000, self.update_special_timer)
    
    def special_enter(self):
        if not self.special_running:
            self.special_start()
        elif self.special_char:
            ans = self.special_entry.get().strip().upper()
            if ans:
                self.special_check()
                self.root.after(800, self.special_next)
            else:
                self.special_next()
    
    def special_next(self):
        if not self.special_running: return
        chars = self.get_special_chars()
        self.special_char = random.choice(chars)
        self.special_entry.delete(0, tk.END)
        self.special_display.config(text="?", fg=self.GREEN)
        self.special_name_lbl.config(text="")
        self.special_feedback.config(text="Écoutez...", fg=self.DIM)
        self.play_special(self.special_char)
        self.special_entry.focus()
    
    def special_check(self):
        if not self.special_char: return
        ans = self.special_entry.get().strip().upper()
        if not ans: return
        
        self.special_total += 1
        name, morse = SPECIAL_CHARS[self.special_char]
        
        if ans == self.special_char:
            self.special_correct += 1
            self.special_display.config(text=self.special_char, fg=self.GREEN)
            self.special_feedback.config(text=f"✓ {name} ({morse})", fg=self.GREEN)
        else:
            self.special_display.config(text=self.special_char, fg=self.RED)
            self.special_feedback.config(text=f"✗ C'était {self.special_char} - {name} ({morse})", fg=self.RED)
        
        self.special_name_lbl.config(text=name)
        pct = (self.special_correct / self.special_total * 100) if self.special_total > 0 else 0
        self.special_stats_lbl.config(text=f"Score: {self.special_correct}/{self.special_total} ({pct:.0f}%)")

    # ════════════════════════════════════════════════════════════════
    # INDICATIFS
    # ════════════════════════════════════════════════════════════════
    
    def show_call(self):
        self.call_correct = 0
        self.call_total = 0
        
        main = tk.Frame(self.content, bg=self.BG)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main, text="📻 Entraînement Indicatifs", font=('Arial', 14, 'bold'), 
                fg=self.PURPLE, bg=self.BG).pack(pady=(0,15))
        
        # Config
        cfg = tk.Frame(main, bg=self.BG)
        cfg.pack(pady=10)
        
        tk.Label(cfg, text="Pays :", font=('Arial', 10), fg=self.TEXT, bg=self.BG).pack(side=tk.LEFT)
        self.pays_combo = ttk.Combobox(cfg, values=["Tous"] + list(CALLSIGN_PREFIXES.keys()), 
                                       state='readonly', width=12)
        self.pays_combo.set("Tous")
        self.pays_combo.pack(side=tk.LEFT, padx=10)
        
        tk.Label(cfg, text="Durée :", font=('Arial', 10), fg=self.TEXT, bg=self.BG).pack(side=tk.LEFT, padx=(20,0))
        self.call_dur_combo = ttk.Combobox(cfg, values=["2", "5", "10", "15", "∞"], width=5, state='readonly')
        self.call_dur_combo.set("5")
        self.call_dur_combo.pack(side=tk.LEFT, padx=5)
        tk.Label(cfg, text="min", font=('Arial', 10), fg=self.DIM, bg=self.BG).pack(side=tk.LEFT)
        
        # Stats
        stats_f = tk.Frame(main, bg=self.BG)
        stats_f.pack(pady=10)
        self.call_timer_lbl = tk.Label(stats_f, text="⏱ --:--", font=('Arial', 12), fg=self.ORANGE, bg=self.BG)
        self.call_timer_lbl.pack(side=tk.LEFT, padx=15)
        self.call_stats_lbl = tk.Label(stats_f, text="Score: 0/0", font=('Arial', 12), fg=self.TEXT, bg=self.BG)
        self.call_stats_lbl.pack(side=tk.LEFT, padx=15)
        
        # Display
        self.call_display = tk.Label(main, text="?", font=('Consolas', 48, 'bold'), fg=self.DIM, bg=self.BG)
        self.call_display.pack(pady=15)
        self.call_country_lbl = tk.Label(main, text="", font=('Arial', 10), fg=self.PURPLE, bg=self.BG)
        self.call_country_lbl.pack()
        
        # Entry
        self.call_entry = tk.Entry(main, font=('Consolas', 24), width=12, justify=tk.CENTER,
                                  bg=self.BG3, fg=self.PURPLE, insertbackground=self.PURPLE)
        self.call_entry.pack(pady=10)
        self.call_entry.bind('<Return>', lambda e: self.call_enter())
        
        # Feedback
        self.call_feedback = tk.Label(main, text="Appuyez sur Démarrer", font=('Arial', 11), fg=self.DIM, bg=self.BG)
        self.call_feedback.pack(pady=5)
        
        # Boutons
        btns = tk.Frame(main, bg=self.BG)
        btns.pack(pady=10)
        self.call_btn = tk.Button(btns, text="▶ Démarrer", font=('Arial', 11), 
                                 fg='white', bg=self.GREEN, relief=tk.FLAT, padx=20, pady=8,
                                 command=self.call_start)
        self.call_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="🔄 Rejouer", font=('Arial', 11), 
                 fg='white', bg=self.ORANGE, relief=tk.FLAT, padx=20, pady=8,
                 command=lambda: self.play(self.call_current) if self.call_current else None).pack(side=tk.LEFT, padx=5)
        self.call_stop_btn = tk.Button(btns, text="⏹ Stop", font=('Arial', 11), 
                                      fg='white', bg=self.RED, relief=tk.FLAT, padx=20, pady=8,
                                      command=self.call_stop, state=tk.DISABLED)
        self.call_stop_btn.pack(side=tk.LEFT, padx=5)
    
    def call_start(self):
        dur = self.call_dur_combo.get()
        self.call_duration = 9999 if dur == "∞" else int(dur)
        self.call_start_time = datetime.now()
        self.call_running = True
        self.call_correct = 0
        self.call_total = 0
        self.call_btn.config(state=tk.DISABLED)
        self.call_stop_btn.config(state=tk.NORMAL)
        self.update_call_timer()
        self.call_next()
    
    def call_stop(self):
        self.call_running = False
        self.call_btn.config(state=tk.NORMAL)
        self.call_stop_btn.config(state=tk.DISABLED)
        self.call_feedback.config(text="Entraînement terminé", fg=self.ORANGE)
    
    def update_call_timer(self):
        if not self.call_running: return
        elapsed = datetime.now() - self.call_start_time
        remain = timedelta(minutes=self.call_duration) - elapsed
        if remain.total_seconds() <= 0:
            self.call_stop()
            return
        m, s = int(remain.total_seconds() // 60), int(remain.total_seconds() % 60)
        if self.call_duration < 9999:
            self.call_timer_lbl.config(text=f"⏱ {m}:{s:02d}", fg=self.RED if remain.total_seconds() < 60 else self.ORANGE)
        else:
            em, es = int(elapsed.total_seconds() // 60), int(elapsed.total_seconds() % 60)
            self.call_timer_lbl.config(text=f"⏱ {em}:{es:02d}", fg=self.ORANGE)
        self.root.after(1000, self.update_call_timer)
    
    def call_enter(self):
        if not self.call_running:
            self.call_start()
        elif self.call_current:
            ans = self.call_entry.get().strip().upper()
            if ans:
                self.call_check()
                self.root.after(600, self.call_next)
            else:
                self.call_next()
    
    def call_next(self):
        if not self.call_running: return
        pays = self.pays_combo.get()
        pays = None if pays == "Tous" else pays
        self.call_current, self.call_country = generate_callsign(pays)
        self.call_entry.delete(0, tk.END)
        self.call_display.config(text="?", fg=self.PURPLE)
        self.call_country_lbl.config(text="")
        self.call_feedback.config(text="Écoutez...", fg=self.DIM)
        self.play(self.call_current)
        self.call_entry.focus()
    
    def call_check(self):
        if not self.call_current: return
        ans = self.call_entry.get().strip().upper()
        if not ans: return
        
        self.call_total += 1
        if ans == self.call_current:
            self.call_correct += 1
            self.call_feedback.config(text="✓ Correct !", fg=self.GREEN)
        else:
            self.call_feedback.config(text=f"✗ C'était : {self.call_current}", fg=self.RED)
        
        self.call_display.config(text=self.call_current)
        self.call_country_lbl.config(text=f"📍 {self.call_country}")
        pct = (self.call_correct / self.call_total * 100) if self.call_total > 0 else 0
        self.call_stats_lbl.config(text=f"Score: {self.call_correct}/{self.call_total} ({pct:.0f}%)")

    # ════════════════════════════════════════════════════════════════
    # CONTEST
    # ════════════════════════════════════════════════════════════════
    
    def show_contest(self):
        self.contest_qsos = 0
        
        main = tk.Frame(self.content, bg=self.BG)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main, text="🏆 Mode Contest", font=('Arial', 14, 'bold'), 
                fg=self.ORANGE, bg=self.BG).pack(pady=(0,15))
        
        # Config
        cfg = tk.Frame(main, bg=self.BG)
        cfg.pack(pady=10)
        tk.Label(cfg, text="Durée :", font=('Arial', 10), fg=self.TEXT, bg=self.BG).pack(side=tk.LEFT)
        self.contest_dur_combo = ttk.Combobox(cfg, values=["2", "5", "10", "15", "30"], width=5, state='readonly')
        self.contest_dur_combo.set("5")
        self.contest_dur_combo.pack(side=tk.LEFT, padx=5)
        tk.Label(cfg, text="min", font=('Arial', 10), fg=self.DIM, bg=self.BG).pack(side=tk.LEFT)
        
        # Stats
        stats_f = tk.Frame(main, bg=self.BG)
        stats_f.pack(pady=10)
        self.contest_qso_lbl = tk.Label(stats_f, text="QSOs: 0", font=('Arial', 14, 'bold'), fg=self.TEXT, bg=self.BG)
        self.contest_qso_lbl.pack(side=tk.LEFT, padx=20)
        self.contest_timer_lbl = tk.Label(stats_f, text="⏱ 5:00", font=('Arial', 14), fg=self.ORANGE, bg=self.BG)
        self.contest_timer_lbl.pack(side=tk.LEFT, padx=20)
        
        # Display
        self.contest_display = tk.Label(main, text="Prêt ?", font=('Consolas', 48, 'bold'), fg=self.DIM, bg=self.BG)
        self.contest_display.pack(pady=15)
        self.contest_country_lbl = tk.Label(main, text="", font=('Arial', 10), fg=self.PURPLE, bg=self.BG)
        self.contest_country_lbl.pack()
        
        # Entry
        self.contest_entry = tk.Entry(main, font=('Consolas', 24), width=12, justify=tk.CENTER,
                                     bg=self.BG3, fg=self.ORANGE, insertbackground=self.ORANGE)
        self.contest_entry.pack(pady=10)
        self.contest_entry.bind('<Return>', lambda e: self.contest_check() if self.contest_on else self.contest_start())
        
        # Feedback
        self.contest_feedback = tk.Label(main, text="", font=('Arial', 11), bg=self.BG)
        self.contest_feedback.pack(pady=5)
        
        # Boutons
        btns = tk.Frame(main, bg=self.BG)
        btns.pack(pady=10)
        self.contest_btn = tk.Button(btns, text="🚀 Démarrer", font=('Arial', 11), 
                                    fg='white', bg=self.GREEN, relief=tk.FLAT, padx=20, pady=8,
                                    command=self.contest_start)
        self.contest_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="🔄 Rejouer", font=('Arial', 11), 
                 fg='white', bg=self.ORANGE, relief=tk.FLAT, padx=20, pady=8,
                 command=lambda: self.play(self.contest_call) if self.contest_call else None).pack(side=tk.LEFT, padx=5)
    
    def contest_start(self):
        self.contest_duration = int(self.contest_dur_combo.get())
        self.contest_start_time = datetime.now()
        self.contest_on = True
        self.contest_qsos = 0
        self.contest_btn.config(state=tk.DISABLED)
        self.update_contest_timer()
        self.contest_next()
    
    def update_contest_timer(self):
        if not self.contest_on: return
        elapsed = datetime.now() - self.contest_start_time
        remain = timedelta(minutes=self.contest_duration) - elapsed
        if remain.total_seconds() <= 0:
            self.contest_end()
            return
        m, s = int(remain.total_seconds() // 60), int(remain.total_seconds() % 60)
        self.contest_timer_lbl.config(text=f"⏱ {m}:{s:02d}", fg=self.RED if remain.total_seconds() < 60 else self.ORANGE)
        self.root.after(1000, self.update_contest_timer)
    
    def contest_next(self):
        if not self.contest_on: return
        self.contest_call, self.contest_country = generate_callsign()
        self.contest_entry.delete(0, tk.END)
        self.contest_display.config(text="?", fg=self.ORANGE)
        self.contest_country_lbl.config(text="")
        self.contest_feedback.config(text="")
        self.play(self.contest_call)
        self.contest_entry.focus()
    
    def contest_check(self):
        if not self.contest_on or not self.contest_call: return
        ans = self.contest_entry.get().strip().upper()
        if not ans: return
        
        if ans == self.contest_call:
            self.contest_qsos += 1
            self.contest_feedback.config(text="✓ QSO !", fg=self.GREEN)
        else:
            self.contest_feedback.config(text=f"✗ {self.contest_call}", fg=self.RED)
        
        self.contest_display.config(text=self.contest_call)
        self.contest_country_lbl.config(text=f"📍 {self.contest_country}")
        self.contest_qso_lbl.config(text=f"QSOs: {self.contest_qsos}")
        self.root.after(600, self.contest_next)
    
    def contest_end(self):
        self.contest_on = False
        self.contest_display.config(text="Terminé !", fg=self.GREEN)
        self.contest_feedback.config(text=f"Score final : {self.contest_qsos} QSOs", fg=self.ORANGE)
        self.contest_timer_lbl.config(text="⏱ 0:00")
        self.contest_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
