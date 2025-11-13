#!/usr/bin/env python3

import rarfile
import zipfile
import json
import shutil
from pathlib import Path
from datetime import date, datetime
import os
import requests
import process_cheats


def version_parser(version):
    year = int(version[4:8])
    month = int(version[0:2])
    day = int(version[2:4])
    return date(year, month, day)


class DatabaseInfo:
    def __init__(self):
        self.database_version_url = "https://github.com/HamletDuFromage/switch-cheats-db/releases/latest/download/VERSION"
        self.database_version = self.fetch_database_version()

    def fetch_database_version(self):
        version = requests.get(self.database_version_url).text.strip()
        return date.fromisoformat(version)

    def get_database_version(self):
        return self.database_version


# 🆕 Reemplazo directo de GbatempCheatsInfo
class VampitechCheatsInfo:
    def __init__(self):
        self.page_url = "https://vampitech.net/switch/cheats/titles.rar"
        self.vampitech_version = self.fetch_vampitech_version()

    def fetch_vampitech_version(self):
        """Obtiene la fecha del archivo remoto desde la cabecera HTTP."""
        response = requests.head(self.page_url, allow_redirects=True)
        last_modified = response.headers.get("Last-Modified")

        if last_modified:
            version_date = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z").date()
        else:
            # Si no hay cabecera, usar la fecha actual
            version_date = date.today()

        return version_date

    def has_new_cheats(self, database_version):
        return self.vampitech_version > database_version

    def get_vampitech_version(self):
        return self.vampitech_version

    def get_download_url(self):
        return self.page_url


class HighFPSCheatsInfo:
    def __init__(self):
        self.download_url = "https://github.com/ChanseyIsTheBest/NX-60FPS-RES-GFX-Cheats/archive/refs/heads/main.zip"
        self.api_url = "https://api.github.com/repos/ChanseyIsTheBest/NX-60FPS-RES-GFX-Cheats/branches/main"
        self.highfps_version = self.fetch_high_FPS_cheats_version()

    def fetch_high_FPS_cheats_version(self):
        token = os.getenv('GITHUB_TOKEN')
        headers = {'Authorization': f'token {token}'} if token else {}
        repo_info = requests.get(self.api_url, headers=headers).json()
        last_commit_date = repo_info.get("commit", {}).get("commit", {}).get("author", {}).get("date")
        return date.fromisoformat(last_commit_date.split("T")[0]) if last_commit_date else date.today()

    def has_new_cheats(self, database_version):
        return self.highfps_version > database_version

    def get_high_FPS_version(self):
        return self.highfps_version

    def get_download_url(self):
        return self.download_url


class ArchiveWorker():
    def download_archive(self, url, path):
        print(f"Descargando archivo desde: {url}")
        response = requests.get(url, allow_redirects=True, stream=True)
        print("Status code:", response.status_code)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Tamaño reportado:", response.headers.get("Content-Length"))

        # Guarda los primeros 200 bytes para inspeccionar si es HTML o RAR
        preview = response.raw.read(200)
        print("Bytes iniciales:", preview[:60])

        # Reinicia la descarga correctamente
        response = requests.get(url, allow_redirects=True)
        with open(path, "wb") as f:
            f.write(response.content)

    def extract_archive(self, path, extract_path=None):
        if rarfile.is_rarfile(path):
            rf = rarfile.RarFile(path)
            rf.extractall(path=extract_path)
        elif zipfile.is_zipfile(path):
            zf = zipfile.ZipFile(path)
            zf.extractall(path=extract_path)
        else:
            return False
        return True

    def build_cheat_files(self, cheats_path, out_path):
        cheats_path = Path(cheats_path)
        titles_path = Path(out_path).joinpath("titles")
        if not titles_path.exists():
            titles_path.mkdir(parents=True)
        for tid in cheats_path.iterdir():
            tid_path = titles_path.joinpath(tid.stem)
            tid_path.mkdir(exist_ok=True)
            with open(tid, "r") as cheats_file:
                cheats_dict = json.load(cheats_file)
            for key, value in cheats_dict.items():
                if key == "attribution":
                    for author, content in value.items():
                        with open(tid_path.joinpath(author), "w") as attribution_file:
                            attribution_file.write(content)
                else:
                    cheats_folder = tid_path.joinpath("cheats")
                    cheats_folder.mkdir(exist_ok=True)
                    cheats = ""
                    for _, content in value.items():
                        cheats += content
                    if cheats:
                        with open(cheats_folder.joinpath(f"{key}.txt"), "w") as bid_file:
                            bid_file.write(cheats)

    def touch_all(self, path):
        for p in path.rglob("*"):
            if p.is_file():
                p.touch()

    def create_archives(self, out_path):
        out_path = Path(out_path)
        titles_path = out_path.joinpath("titles")
        self.touch_all(titles_path)
        shutil.make_archive(str(titles_path.resolve()), "zip", root_dir=out_path, base_dir="titles")
        contents_path = titles_path.rename(titles_path.parent.joinpath("contents"))
        self.touch_all(contents_path)
        shutil.make_archive(str(contents_path.resolve()), "zip", root_dir=out_path, base_dir="contents")

    def create_version_file(self, out_path="."):
        with open(f"{out_path}/VERSION", "w") as version_file:
            version_file.write(str(date.today()))


def count_cheats(cheats_directory):
    n_games = 0
    n_updates = 0
    n_cheats = 0
    for json_file in Path(cheats_directory).glob('*.json'):
        with open(json_file, 'r') as file:
            cheats = json.load(file)
            for bid in cheats.values():
                n_cheats += len(bid)
                n_updates += 1
        n_games += 1

    readme_file = Path('README.md')
    if readme_file.exists():
        with readme_file.open('r') as file:
            lines = file.readlines()
        lines[-1] = f"{n_cheats} cheats in {n_games} titles/{n_updates} updates"
        with readme_file.open('w') as file:
            file.writelines(lines)


if __name__ == '__main__':
    cheats_path = "cheats"
    cheats_vampi_path = "cheats_gbatemp"
    cheats_gfx_path = "cheats_gfx"
    archive_path = "titles.rar"

    database = DatabaseInfo()
    database_version = database.get_database_version()
    highfps = HighFPSCheatsInfo()
    vampitech = VampitechCheatsInfo()

    if vampitech.has_new_cheats(database_version) or highfps.has_new_cheats(database_version):
        archive_worker = ArchiveWorker()

        print(f"Descargando cheats desde Vampitech...")
        archive_worker.download_archive(vampitech.get_download_url(), archive_path)
        archive_worker.extract_archive(archive_path, "gbatemp")

        print("Descargando cheats High FPS...")
        archive_worker.download_archive(highfps.get_download_url(), "highfps.zip")
        archive_worker.extract_archive("highfps.zip")

        print("Procesando archivos...")
        process_cheats.ProcessCheats("gbatemp/titles", cheats_vampi_path)
        process_cheats.ProcessCheats("NX-60FPS-RES-GFX-Cheats-main/titles", cheats_gfx_path)
        process_cheats.ProcessCheats("gbatemp/titles", cheats_path)
        process_cheats.ProcessCheats("NX-60FPS-RES-GFX-Cheats-main/titles", cheats_path)

        print("Construyendo archivos completos de cheats...")
        out_path = Path("complete")
        out_path.mkdir(exist_ok=True)
        archive_worker.build_cheat_files(cheats_path, out_path)

        print("Creando archivos comprimidos...")
        archive_worker.create_archives("complete")
        archive_worker.create_archives("NX-60FPS-RES-GFX-Cheats-main")
        archive_worker.create_archives("gbatemp")

        archive_worker.create_version_file()

        count_cheats(cheats_path)
    else:
        print("Todo está actualizado.")
