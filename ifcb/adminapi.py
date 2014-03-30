from flask import Flask, jsonify, abort

# IFCB restful configuration API
# written by Mark Nye (marknye@clubofhumanbeings.com), March 2014

def validate_path(path):
    pass

app = Flask(__name__)
app.debug = True

BASEPATH = '/admin/api/v1.0'

@app.route(BASEPATH + '/timeseries', methods = ['GET'])
# return all timeseries configurations
def get_timeseries_list():
    pass

@app.route(BASEPATH + '/timeseries/<int:timeseries_id>', methods = ['GET'])
# return select timeseries configuration
def get_timeseries(timeseries_id):
    pass

@app.route(BASEPATH + '/timeseries', methods = ['POST'])
# create timeseries configuration
def create_timeseries():
    pass

@app.route(BASEPATH + '/timeseries/<int:timeseries_id>', methods = ['PUT'])
# update timeseries configuration
def update_timeseries():
    pass

@app.route(BASEPATH + '/timeseries/<int:timeseries_id>', methods = ['DELETE'])
# delete timeseries configuration
def delete_timeseries():
    pass


if __name__=='__main__':
    app.run(host='0.0.0.0',port=8080)
