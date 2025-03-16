from typing import Union
import urllib.request
from pathlib import Path
from intel_simd_knowledge_toy.data_tools.network._utils import _DownloadProgress

def download_url(url: str, target_file: Union[str, Path]):
    target_file_p = Path(target_file)
    target_file_s = str(target_file_p)
    is_overwriting = target_file_p.exists()
    if not target_file_p.parent.exists():
        target_file_p.parent.mkdir(parents=True)
    download_or_overwrite_s = "Overwriting: " if is_overwriting else "Downloading to: "
    print("Download from: " + url)
    print(download_or_overwrite_s + target_file_s)
    progress = _DownloadProgress(print)
    urllib.request.urlretrieve(url, target_file_s, reporthook=progress)
    print("Download complete.")

if __name__ == "__main__":
    pass
