import tempfile
import shutil
import mimetypes

FORMATS_BY_MIME_TYPE = {
'image/jpeg': 'JPEG',
'image/png': 'PNG',
'image/tiff': 'TIFF',
'image/gif': 'GIF',
'image/x-ms-bmp': 'BMP',
'image/x-portable-pixmap': 'PPM',
'image/x-xbitmap': 'XBM'
}

def mimetype2format(mimetype):
    return FORMATS_BY_MIME_TYPE[mimetype]

def filename2format(filename):
    (mimetype, _) = mimetypes.guess_type(filename)
    return mimetype2format(mimetype)
    
def stream_image(image,format,out):
    with tempfile.SpooledTemporaryFile() as flo:
        image.save(flo,format)
        flo.seek(0)
        shutil.copyfileobj(flo,out)
           
def thumbnail(image, wh):
    image.thumbnail(wh, Image.ANTIALIAS)
    return image
