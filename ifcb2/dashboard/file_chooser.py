import os
from flask import Flask, abort, request, Response
from jinja2 import Environment
from lxml import html

RESPONSE_TEMPLATE="""<ul class="jqueryFileTree" style="display: none;">
{% for dir in dirs %}  <li class="directory collapsed"><a href="#" rel="{{dir['rel_path']}}/">{{dir['name']}}</a></li>
{% endfor %}
{% for file in files %} <li class="file ext_{{file['ext']}}"><a href="#" rel="{{file['rel_path']}}">{{file['name']}}</a></li>
{% endfor %}
</ul>"""

ROOT_DIR='/home/jfutrelle'

def list_dir(rel_dir):
    abs_dir = os.path.join(ROOT_DIR, rel_dir)
    print (rel_dir, abs_dir)
    dirs = []
    files = []
    for name in os.listdir(abs_dir):
        abs_path = os.path.join(abs_dir, name)
        rel_path = os.path.join(rel_dir, name);
        rec = dict(rel_path=rel_path, name=name)
        if os.path.isdir(abs_path):
            dirs.append(rec)
        elif os.path.isfile(abs_path):
            try:
                rec['ext'] = os.path.splitext(name)[1][1:]
            except:
                rec['ext'] = ''
            files.append(rec)
    def name_key(thing):
        return thing['name']
    dirs.sort(key=name_key)
    files.sort(key=name_key)
    return dirs, files

def render_template(dirs, files):
    bindings = dict(dirs=dirs, files=files)
    return Environment().from_string(RESPONSE_TEMPLATE).render(**bindings)

#### flask

app = Flask(__name__, static_folder='/home/jfutrelle/file_browsing/static')

@app.route('/file_chooser',methods=['POST'])
def connector():
    rel_dir = html.fromstring(request.form['dir']).text
    return Response(render_template(*list_dir(rel_dir)),mimetype='text/plain')

if __name__=='__main__':
    app.debug=True
    app.run(host='0.0.0.0')
