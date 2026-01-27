# backend/core/constants.py

COLORS = {
    'A': '#e9003a', 'B': '#0073ba', 'C': '#f78e1e', 'D': '#009e49',
    'VICE': '#e74c3c', 'GENTRIFICATION': '#3498db',
    'NUISANCE': '#f39c12', 'SUPERSTITION': '#9b59b6',
    'IMMO': '#2ecc71'
}

# Liste enrichie des mots-clés
KEYWORDS = {
    'SUPERSTITION': [
        'cimetiere', 'cimetière', 'tombe', 'sepulture', 'sépulture', 
        'funeraire', 'funéraire', 'pompes funebres', 'pompes funèbres', 'thanatopraxie', 
        'crematorium', 'crématorium', 'mort', 'deces', 'décès', 'obseques', 'obsèques',
        'hopital', 'hôpital', 'clinique', 'ehpad', 'sante', 'santé', 'medical', 'médical',
        'eglise', 'église', 'cathedrale', 'temple', 'mosquee', 'mosquée', 'synagogue', 
        'culte', 'paroisse', 'chapelle', 'saint', 'st ', 'notre dame', 'dieu', 'croix',
        'esoterisme', 'ésotérisme', 'voyance'
    ],
    'NUISANCE': [
        'ecole', 'école', 'creche', 'crèche', 'college', 'lycee', 
        'aire de jeu', 'parc enfant', 'toboggan', 'skate', 'city stade',
        'gare', 'train', 'metro', 'bus', 'tram', 'aeroport', 
        'usine', 'garage', 'essence', 'station service', 'pompier', 'police',
        'bruit', 'discotheque', 'boite de nuit', 'club'
    ],
    'VICE': [
        'sex', 'strip', 'libertin', 'charme', 'sauna',
        'bar', 'pub', 'alcool', 'biere', 'vin', 
        'tabac', 'vape', 'cbd', 'chicha',
        'casino', 'pari', 'jeux', 
        'kebab', 'tacos', 'burger', 'fast food'
    ]
}

ALL_STATIONS = [
    {"nom": "Perrache", "lat": 45.7485, "lon": 4.8266, "c": COLORS['A']},
    {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322, "c": COLORS['A']},
    {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "c": COLORS['A']},
    {"nom": "Charpennes", "lat": 45.7710, "lon": 4.8636, "c": COLORS['A']},
    {"nom": "Vaulx-en-Velin La Soie", "lat": 45.7607, "lon": 4.9298, "c": COLORS['A']},
    {"nom": "Part-Dieu", "lat": 45.7601, "lon": 4.8590, "c": COLORS['B']},
    {"nom": "Saxe-Gambetta", "lat": 45.7516, "lon": 4.8486, "c": COLORS['B']},
    {"nom": "Gare d'Oullins", "lat": 45.7161, "lon": 4.8138, "c": COLORS['B']},
    {"nom": "Croix-Rousse", "lat": 45.7745, "lon": 4.8315, "c": COLORS['C']},
    {"nom": "Cuire", "lat": 45.7852, "lon": 4.8338, "c": COLORS['C']},
    {"nom": "Gare de Vaise", "lat": 45.7797, "lon": 4.8051, "c": COLORS['D']},
    {"nom": "Vieux Lyon", "lat": 45.7598, "lon": 4.8268, "c": COLORS['D']},
    {"nom": "Grange Blanche", "lat": 45.7434, "lon": 4.8763, "c": COLORS['D']},
    {"nom": "Gare de Vénissieux", "lat": 45.7047, "lon": 4.8879, "c": COLORS['D']},
]