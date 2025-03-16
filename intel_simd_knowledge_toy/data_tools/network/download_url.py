from typing import Union
import urllib.request
from pathlib import Path
from intel_simd_knowledge_toy.data_tools.network._utils import _DownloadProgress

def download_url(url: str, target_file: Union[str, Path]):
    target_file = str(Path(target_file))
    print("Download from: " + url)
    print("Download to: " + target_file)
    progress = _DownloadProgress(print)
    urllib.request.urlretrieve(url, target_file, reporthook=progress)
    print("Download complete.")

if __name__ == "__main__":
    pass
