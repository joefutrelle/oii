from flask import Response
import mimetypes
from oii.image.io import as_pil
from oii.image.pil.utils import filename2format
from StringIO import StringIO

def image_types(filename):
    # now determine PIL format and MIME type
    pil_format = filename2format(filename)
    (mimetype, _) = mimetypes.guess_type(filename)
    return (pil_format, mimetype)

def image_response(image,filename):
    (format,mimetype) = image_types(filename)
    """Construct a Flask Response object for the given image, PIL format, and MIME type."""
    image = as_pil(image)
    buf = StringIO()
    if format == 'JPEG':
        im = image.save(buf,format,quality=85)
    else:
        im = image.save(buf,format)
    return Response(buf.getvalue(), mimetype=mimetype)
