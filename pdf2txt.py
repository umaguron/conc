"""
Install pdfminer.six before use this script.
pip install pdfminer.six
"""

import pathlib
import settings
from pdfminer.high_level import extract_text
import glob
import re
import os
fileDir = pathlib.Path(__file__).parent.resolve()

def main():
    SAVE_DIR = str(fileDir / "txt_converted")
    FAILED_DIR = str(fileDir / "txt_converted/failed")
    UNUSED_DIR = str(fileDir / "txt_converted/unused")
    os.makedirs(SAVE_DIR, exist_ok=True)
    os.makedirs(FAILED_DIR, exist_ok=True)
    os.makedirs(UNUSED_DIR, exist_ok=True)

    pdfs = glob.glob(os.path.join(settings.PDF_SEARCH_DIR, "*.pdf"))

    for p in pdfs:
        
        txt_fp = os.path.join(
            SAVE_DIR,
            re.sub(".pdf", ".txt", os.path.basename(p))
        )
        failed_txt_fp = os.path.join(
            FAILED_DIR,
            re.sub(".pdf", ".txt", os.path.basename(p))
        )
        unused_txt_fp = os.path.join(
            UNUSED_DIR,
            re.sub(".pdf", ".txt", os.path.basename(p))
        )
        
        if os.path.isfile(txt_fp) or os.path.isfile(failed_txt_fp) or os.path.isfile(unused_txt_fp):
            print(f"ALREADY EXISTS: {txt_fp}")
        else:
            print(f"CONVERTING ...: {txt_fp}")
            try:
                t = extract_text(p, codec="utf-16")
                t1 = re.sub("-\n", "", t)
                t2 = re.sub("\n", " ", t1)
                if len(t2) > 100:
                    with open(txt_fp, "w") as f:
                        f.write(t2)
                else:
                    with open(failed_txt_fp, "w") as f:
                        f.write(' ')
            except:
                print("!!ERROR!!")
                with open(failed_txt_fp, "w") as f:
                    f.write(' ')

if __name__ == "__main__":
    main()