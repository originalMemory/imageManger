# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['tray_start.py'],
             pathex=['D:\\Code\\MyGit\\ImageManager'],
             binaries=[],
             datas=[
                ('config.ini', '.'),
                ('images', 'images')
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='BackgroundAutoChange',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          icon='images/exe.ico',
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='BackgroundAutoChange')
