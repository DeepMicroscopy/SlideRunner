# -*- mode: python -*-

block_cipher = None

a = Analysis(['main.py'],
             pathex=[],
             binaries=[('libopenslide-0.dll','.')],
             datas=[('SlideRunner/artwork/*.png','SlideRunner/artwork'),
                    ('SlideRunner/plugins/*.*','SlideRunner/plugins')],
             hiddenimports=['openslide','shapely','sklearn', 'scipy.ndimage', 'sklearn.neighbors.typedefs', 'sklearn.neighbors.quadtree'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
for d in a.datas:
    if '_C.cp37-win_amd64.pyd' in d[0]:
        a.datas.remove(d)
        break
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
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
          runtime_tmpdir=None,
          console=False)
