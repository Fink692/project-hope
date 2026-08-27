from pathlib import Path
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

repository = Path(SPECPATH).resolve().parents[2]
core = repository / "services" / "core"
sys.path.insert(0, str(core))
os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
os.environ["DJANGO_ENV"] = "development"
os.environ["DATABASE_URL"] = ""
os.environ["VALKEY_URL"] = ""

packages = ["django", "rest_framework", "identity", "modules", "audit", "project"]
hiddenimports = ["fastapi", "pydantic", "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl", "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.off"]
datas = [(str(repository / "services" / "ai-gateway" / "main.py"), ".")]
for package in packages:
    hiddenimports += collect_submodules(package, filter=lambda name: ".test" not in name and "desktop_settings" not in name, on_error="warn once")
    datas += collect_data_files(package, include_py_files=True, excludes=["**/__pycache__/**", "**/test*.py"])
hiddenimports += ["project.desktop_settings", "project.desktop_urls"]

analysis = Analysis([str(core / "desktop_runtime.py")], pathex=[str(core)], binaries=[], datas=datas, hiddenimports=hiddenimports, excludes=["tkinter", "IPython", "pytest", "mypy"], noarchive=False)
archive = PYZ(analysis.pure)
executable = EXE(archive, analysis.scripts, [], exclude_binaries=True, name="project-hope-core", debug=False, strip=False, upx=False, console=True)
collection = COLLECT(executable, analysis.binaries, analysis.datas, strip=False, upx=False, name="project-hope-core")
