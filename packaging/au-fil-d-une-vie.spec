# Recette PyInstaller : construit « Au fil d'une vie.app » pour macOS.
# Lancement : uv run --group packaging pyinstaller packaging/au-fil-d-une-vie.spec --noconfirm
from PyInstaller.utils.hooks import collect_all, collect_data_files

from au_fil_d_une_vie import __version__

datas = collect_data_files("au_fil_d_une_vie")
binaries = []
hiddenimports = []
# spaCy et ses modèles chargent leurs composants par nom : on embarque tout.
for paquet in ("spacy", "thinc", "fr_core_news_md", "en_core_web_sm", "faster_whisper", "ctranslate2"):
    d, b, h = collect_all(paquet)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["lancer.py"],
    pathex=["../src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "matplotlib", "IPython"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Au fil d'une vie",
    console=False,
    argv_emulation=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Au fil d'une vie")
app = BUNDLE(
    coll,
    name="Au fil d'une vie.app",
    icon="../assets/icone/icone.icns",
    bundle_identifier="fr.emery.aufildunevie",
    version=__version__,
    info_plist={
        "CFBundleName": "Au fil d'une vie",
        "CFBundleDisplayName": "Au fil d'une vie",
        "CFBundleShortVersionString": __version__,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        # Sans cette phrase, macOS refuse l'accès au micro.
        "NSMicrophoneUsageDescription": (
            "Au fil d'une vie enregistre les entretiens avec tes proches. "
            "Le son reste sur ton ordinateur."
        ),
    },
)
