import os
import sys
from pathlib import Path
import zipfile
import shutil

parent_path = Path(__file__).parent


def get_tg_dir() -> Path:
    tg_dir = parent_path.joinpath(parent_path.name)
    if tg_dir.exists():
        shutil.rmtree(tg_dir)
    tg_dir.mkdir()

    return tg_dir


def copy_files() -> Path:
    tg_dir = get_tg_dir()
    sub_dir = tg_dir.joinpath(parent_path.name)
    sub_dir.mkdir()

    for file in parent_path.glob('*'):
        if file.is_dir():
            if file.name == parent_path.name: continue
            if file.name.startswith('__') or file.name.startswith('.') or file.name == 'dist': continue

            shutil.copytree(file, sub_dir.joinpath(file.name))

        elif file.is_file():
            if file.name == __file__: continue

            shutil.copy(file, sub_dir.joinpath(file.name))

    return tg_dir


def zip_dir(tg_dir) -> None:
    dist = parent_path.joinpath('dist')
    if not dist.exists():
        dist.mkdir(parents=True)
    zip_file = dist.joinpath(f'{parent_path.name}.zip')
    if zip_file.exists():
        os.remove(zip_file)
    # utf-8 encoding
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zip:
        for root, dirs, files in os.walk(tg_dir):
            for file in files:
                zip.write(os.path.join(root, file), arcname=os.path.join(root, file).replace(str(tg_dir), ''))
    print(f'Zip file: {zip_file}')
    shutil.rmtree(tg_dir)
    print('Remove temp dir')
    # move zip file to dist


if __name__ == '__main__':
    tg_dir = copy_files()
    if len(sys.argv) > 1 and sys.argv[1] == "--no-zip":
        dist = parent_path.joinpath('dist')
        if not dist.exists():
            dist.mkdir(parents=True)
        shutil.move(tg_dir, dist)
    else:
        zip_dir(tg_dir)
