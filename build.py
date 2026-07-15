import pathlib

from py2exe import freeze
from py2exe import hooks

# This removes clr from unsupported modules
hooks.windows_excludes = """
_curses
_dummy_threading
_emx_link
_gestalt
_posixsubprocess
ce
console
fcntl
grp
java
org
os2
posix
pwd
site
termios
vms_lib
_memimporter
""".split()

# This will make cffi look its DLLs not in library.zip where only python modules are placed.
# DLLs will be placed near executable file.
def hook_cffi(finder, module):
    finder.add_bootcode("""
from cffi import FFI

def wrapper():
    old_dlopen = FFI.dlopen
    def new_method(self, name, flags=0):
        import pathlib
        base_path = pathlib.Path(sys.executable).parent.absolute()
        library_zip = base_path / 'library.zip'
        path = pathlib.Path(name)
        if path.is_relative_to(library_zip):
            name = str(base_path / path.relative_to(library_zip))
        return old_dlopen(self, name, flags)
    return new_method

FFI.dlopen = wrapper()

del FFI
del wrapper
""")

# Same for clr_loader
def hook_clr_loader(finder, module):
    finder.add_bootcode("""
from clr_loader.types import Runtime

def wrapper():
    old_get_assembly = Runtime.get_assembly
    def new_method(self, assembly_path):
        import pathlib
        base_path = pathlib.Path(sys.executable).parent.absolute()
        library_zip = base_path / 'library.zip'
        path = pathlib.Path(assembly_path)
        if path.is_relative_to(library_zip):
            assembly_path = str(base_path / path.relative_to(library_zip))
        return old_get_assembly(self, assembly_path)
    return new_method

Runtime.get_assembly = wrapper()

del Runtime
del wrapper
""")

hooks.hook_cffi = hook_cffi
hooks.hook_clr_loader = hook_clr_loader

from clr_loader import ffi
ffi_path = pathlib.Path(ffi.__file__).parent / 'dlls' / 'amd64'
import pythonnet
pythonnet_runtime = pathlib.Path(pythonnet.__file__).parent / 'runtime'
import prometheus_win_temp
libre_lib_path = pathlib.Path(prometheus_win_temp.__file__).parent / 'libre'

freeze(
    console=[
        {
            'script': 'prometheus_win_temp/main.py',
            'dest_base': 'prometheus_win_temp',
            'cmdline_style': 'pywin32',
            'optimize': 2,
            'compressed': 1,
        }
    ],
    service=[
        {
            'dest_base': 'service.exe',
            'modules': 'prometheus_win_temp.main',
            'cmdline_style': 'pywin32',
            'optimize': 2,
            'compressed': 1,
        }
    ],
    options={
        'includes': [
            'encodings',
            'clr',
            'clr_loader',
            'sentry_sdk.integrations.argv',
            'sentry_sdk.integrations.atexit',
            'sentry_sdk.integrations.excepthook',
            'sentry_sdk.integrations.logging',
            'sentry_sdk.integrations.modules',
            'sentry_sdk.integrations.stdlib',
            'sentry_sdk.integrations.threading',
        ],
        'excludes': [
            'asyncio',
            'tkinter'
        ],
    },
    data_files=[
        ('clr_loader\\ffi\\dlls\\amd64', [str(ffi_path /  'ClrLoader.dll'), str(ffi_path / 'ClrLoader.pdb')]),
        ('pythonnet\\runtime', list(str(p) for p in pythonnet_runtime.iterdir())),
        ('libre', list(str(p) for p in libre_lib_path.iterdir())),
    ]
)