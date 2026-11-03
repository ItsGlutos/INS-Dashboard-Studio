# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec do INS Dashboard Studio.

Gera uma distribuição *onedir* (pasta com o .exe + dependências), que inicia
bem mais rápido que o modo *onefile* — este último descompacta PyQt6 e pandas
em uma pasta temporária a cada execução.

Uso (o script build_exe.ps1 automatiza tudo):

    pyinstaller --noconfirm --clean ins_dashboard.spec
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = Path(SPECPATH)

# Imports feitos em tempo de execução (importlib / import dentro de funções)
# que a análise estática do PyInstaller não enxerga.
hiddenimports = [
    "win32com",
    "win32com.client",
    "pythoncom",
    "pywintypes",
    "win32timezone",
    "python_calamine",
    "openpyxl",
    *collect_submodules("xlwings"),
]

# Módulos opcionais que nunca são usados pelo aplicativo. Removê-los diminui
# a pasta final e o tempo de inicialização.
excludes = [
    "tkinter",
    "unittest",
    "doctest",
    "pydoc",
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
    "matplotlib",
    "scipy",
    "sqlite3",
    "pandas.tests",
    "numpy.tests",
    "PyQt6.QtNetwork",
    "PyQt6.QtQml",
    "PyQt6.QtQuick",
    "PyQt6.QtQuickWidgets",
    "PyQt6.QtQuick3D",
    "PyQt6.QtSql",
    "PyQt6.QtTest",
    "PyQt6.QtMultimedia",
    "PyQt6.QtMultimediaWidgets",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebChannel",
    "PyQt6.QtWebSockets",
    "PyQt6.QtPdf",
    "PyQt6.QtPdfWidgets",
    "PyQt6.QtPositioning",
    "PyQt6.QtLocation",
    "PyQt6.QtBluetooth",
    "PyQt6.QtNfc",
    "PyQt6.QtSensors",
    "PyQt6.QtSerialPort",
    "PyQt6.QtTextToSpeech",
    "PyQt6.QtCharts",
    "PyQt6.QtDataVisualization",
    "PyQt6.QtGraphs",
    "PyQt6.Qt3DCore",
    "PyQt6.Qt3DRender",
    "PyQt6.Qt3DInput",
    "PyQt6.Qt3DLogic",
    "PyQt6.Qt3DAnimation",
    "PyQt6.Qt3DExtras",
    "PyQt6.QtDesigner",
    "PyQt6.QtHelp",
    "PyQt6.QtUiTools",
]

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / "ui" / "assets" / "fonts"), "ui/assets/fonts"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="INS Dashboard Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "line-chart.ico"),
    version=str(PROJECT_ROOT / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="INS Dashboard Studio",
)
