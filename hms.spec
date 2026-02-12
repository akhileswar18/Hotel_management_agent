# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Hotel Management System

Bundles the FastAPI backend + Flet UI into a single Windows executable.
The launcher starts both services so users only need to double-click one file.

Build:
    pyinstaller hms.spec

Output:
    dist/HMS.exe  (single-file executable)
"""

import os
from pathlib import Path

block_cipher = None

# Project root (where this .spec file lives)
PROJECT_ROOT = os.path.abspath(os.path.dirname(SPECPATH) if 'SPECPATH' in dir() else '.')

a = Analysis(
    # Entry point — unified launcher
    [os.path.join(PROJECT_ROOT, 'src', 'launcher.py')],

    pathex=[PROJECT_ROOT],

    binaries=[],

    # Data files to bundle alongside the executable
    datas=[
        # SQL migration files (needed for DB init on first run)
        (os.path.join(PROJECT_ROOT, 'migrations', '*.sql'), 'migrations'),
        (os.path.join(PROJECT_ROOT, 'migrations', '__init__.py'), 'migrations'),
        (os.path.join(PROJECT_ROOT, 'migrations', 'runner.py'), 'migrations'),

        # Environment template (copied to user dir on first run)
        (os.path.join(PROJECT_ROOT, '.env.example'), '.'),

        # Package init files
        (os.path.join(PROJECT_ROOT, 'src', '__init__.py'), 'src'),
    ],

    # Hidden imports that PyInstaller may not auto-detect
    hiddenimports=[
        # FastAPI and dependencies
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'starlette',
        'pydantic',
        'pydantic_core',
        'pydantic_settings',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',

        # Flet
        'flet',
        'flet_core',
        'flet_runtime',

        # HMS modules
        'src',
        'src.domain',
        'src.domain.entities',
        'src.domain.value_objects',
        'src.domain.business_rules',
        'src.application',
        'src.application.services',
        'src.infrastructure',
        'src.infrastructure.database',
        'src.infrastructure.repositories',
        'src.infrastructure.logging_handler',
        'src.api',
        'src.api.app',
        'src.ui',
        'src.ui.app',
        'src.ui.screens',
        'src.ui.screens.auth_screen',
        'src.ui.screens.pos_screen',
        'src.ui.screens.products_screen',
        'src.ui.screens.reports_screen',
        'src.ui.screens.receipt_screen',
        'src.ui.components',
        'src.ui.components.ui_helpers',
        'migrations',
        'migrations.runner',

        # Standard library / extras
        'sqlite3',
        'bcrypt',
        'httpx',
        'aiofiles',
        'python_dateutil',
        'dateutil',
        'json_logger',
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    # Exclude packages not needed at runtime
    excludes=[
        'pytest',
        'pytest_cov',
        'pytest_asyncio',
        'pytest_mock',
        'black',
        'flake8',
        'mypy',
        'pylint',
        'ipdb',
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],

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
    name='HMS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # Show console window (useful for logs/debugging)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,             # TODO: Add HMS icon (hms.ico) in Phase 3
)
