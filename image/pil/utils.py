import tempfile
import shutil

def stream_image(image,format,out):
    with tempfile.SpooledTemporaryFile() as flo:
        image.save(flo,format)
        flo.seek(0)
        shutil.copyfileobj(flo,out)
