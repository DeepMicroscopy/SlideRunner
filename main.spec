# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('libopenslide-0.dll','.')],
    datas=[('SlideRunner/artwork/*.png','SlideRunner/artwork'),
                    ('SlideRunner/plugins/*.*','SlideRunner/plugins')],
    hiddenimports=['h5py', 'skimage', 'sklearn', 'scipy.ndimage', 'sklearn.neighbors.typedefs', 'sklearn.neighbors.quadtree', 'sklearn.naive_bayes', 'qt_wsi_reg', 'qt_wsi_reg.registration_tree'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SlideRunner',
    debug=False,
    icon='SlideRunner/artwork/icon.ico',
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
