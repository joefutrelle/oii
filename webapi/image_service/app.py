from flask import Flask, Response
from oii.webapi.image_service.stereo import get_img, get_resolver
from oii.webapi.image_service.utils import image_response

app = Flask(__name__)
app.debug = True

RESOLVER_PATH='resolver.xml'

I = get_resolver(RESOLVER_PATH)

@app.route('/image/<path:pid>')
def serve_image(pid):
    hit = I.resolve(pid=pid)
    img = get_img(hit)
    return image_response(img, hit.filename)

# utilities
if __name__=='__main__':
    app.run(host='0.0.0.0',port=8080)

