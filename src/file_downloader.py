from bs4 import BeautifulSoup
from navigator import Navigator
from json import loads
from os import path, makedirs


FILE_DIRECTORY_PAGE = "/dispatch.php/course/files?cid="
FILE_FLAT_PAGE = "/dispatch.php/course/files/flat?cid="
DOWNLOAD_NEWEST_FILES = "/dispatch.php/course/files/newest_files?cid="


def clone_folder_structure_of_course(navigator: Navigator, cid: str, root_dir="./downloads"):
    url = navigator.base_url + FILE_DIRECTORY_PAGE + cid
    clone_folder(navigator, url, root_dir=root_dir)
    print("Done!")

def clone_folder(navigator: Navigator, url, root_dir="./downloads", sub_folder=""): 
    response = navigator.get_url(url)
    soup = BeautifulSoup(response.content, "html.parser")
    form = soup.find(id="files_table_form")
    if not form:
        raise Exception("Invalid URL!")
    data_files = loads(str(form.get("data-files")))
    data_folders = loads(str(form.get("data-folders")))

    for file in data_files:
        # yield file
        download_file(navigator, file.get("download_url"), path.join(sub_folder, file.get("name")), root_dir=root_dir)
        # here could be a potential DB Update
        print(f"{file.get('name')} has been downloaded!")
    for folder in data_folders:
        # yield {"folder": folder, "files": list(clone_folder(navigator, folder.get("url")))}
        clone_folder(navigator, folder.get("url"), root_dir, path.join(sub_folder, folder.get("name")))
        # here could be a potential DB Update
        
def download_file(navigator: Navigator, url, file_name, root_dir="./downloads"):
    response = navigator.get_url(url)
    directories = path.dirname(path.join(root_dir, file_name))
    if not path.exists(directories):
        makedirs(directories)

    with open(path.join(root_dir, file_name), "wb") as f:
        f.write(response.content)
