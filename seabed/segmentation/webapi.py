from oii import resolver
import mimetypes
from oii.image.pil.utils import mimetype2format
from flask import Flask, request, url_for, abort, session, Response, render_template
from PIL import Image
from StringIO import StringIO
from oii.seabed.segmentation.segment import segment

RESOLVER_FILE='/Users/jfutrelle/dev/ibt/oii/seabed/segmentation/resolver.xml'
ROOT='/Users/jfutrelle/dev/seabed/segmentation/coral_imagery/TIFF'

app = Flask(__name__)
app.debug = True

# FIXME tile from IFCB code, should be generalized Flask util
def image_response(image,format,mimetype):
    """Construct a Flask Response object for the given image, PIL format, and MIME type."""
    buf = StringIO()
    im = image.save(buf,format)
    return Response(buf.getvalue(), mimetype=mimetype)

@app.route('/<pid>')
def serve_variant(pid):
    hit = TIFF.resolve(root=ROOT,pid=pid)
    if hit is None: # not found
        abort(404)
    # load the image
    image_file = hit.value
    (mimetype, _) = mimetypes.guess_type('foo.%s' % hit.extension)
    pil_format = mimetype2format(mimetype)
    source_img = Image.open(image_file)
    if hit.variant is None: # user just wants the image
        result_img = source_img
    elif hit.variant == 'mask': # user wants a mask
        mask = segment(source_img)
        if hit.extension != 'gif': # except for GIF ouput, scale up intensity
            result_img = Image.fromarray(mask * 80)
        else:
            result_img = Image.fromarray(mask)
    else:
        abort(404)
    return image_response(result_img, pil_format, mimetype)

if __name__=='__main__':
    # configure the resolvers
    RESOLVER = resolver.parse_stream(RESOLVER_FILE)
    TIFF = RESOLVER['tiff']
    app.run(host='0.0.0.0',port=5050)


