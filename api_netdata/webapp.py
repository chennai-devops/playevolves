from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_marshmallow import Marshmallow

import simplejson as json
import zmq


app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
ma = Marshmallow(app)
CORS(app)

# 0MQ configurations
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.connect(app.config['FORWARDER_URL'])
topic = "netdata"


class ID(object):
    pass

class Server(db.Model):
    sid = db.Column(db.String, primary_key=True)
    server_name = db.Column(db.String, nullable=False)
    server_ip = db.Column(db.String, nullable=False)
    status = db.Column(db.Enum("queued","running", "completed","canceled","failed"), nullable=False)
    url = db.Column(db.String)

    def __init__(self, server_name, server_ip):
        self.sid = id(ID())
        self.server_name = server_name
        self.server_ip = server_ip
        self.status = "queued"


class ServerSchema(ma.ModelSchema):
    class Meta:
        model = Server
        #fields = ('sid', 'server_name', 'server_ip', 'status')


@app.errorhandler(404)
def resource_not_found(e):
    return jsonify({"message": "Resource not found"}), 404

@app.route("/")
def index():
    body = {'GET /servers': 'list all the servers configured with netdata',
            'POST /servers': 'configures and setup proxy to a new netdata host',
            'GET /servers/<id>': 'get details of specific server with id',
            'PUT /servers/<id>': 'update details of specific server with id' }

    return jsonify(body), 200

@app.route("/servers", methods=['GET', 'POST'])
def servers():
    if request.method == 'GET':
        servers = Server.query.all()
        servers_schema = ServerSchema(many=True)
        return_data = servers_schema.dump(servers).data
        return jsonify(return_data), 200
    else:
        data = request.get_json()
        server_name = data["server_name"]
        server_ip = data["server_ip"]
        server = Server(server_name, server_ip)

        db.session.add(server)
        db.session.commit()

        # Send to 0MQ
        payload = json.dumps({"sid": server.sid, "server_name": server_name, "server_ip": server_ip})
        socket.send("{0} {1}".format(topic, payload))

        server_schema = ServerSchema()
        return_data = server_schema.dump(server).data
        return jsonify(return_data), 200

@app.route("/servers/<sid>", methods=['GET', 'PUT'])
def server(sid):
    server = Server.query.filter_by(sid=sid).first()
    if not server:
        abort(404)

    if request.method == 'GET':
        server_schema = ServerSchema()
        return_data = server_schema.dump(server).data
        return jsonify(return_data), 200
    else:
        data = request.get_json()
        server.status = data["status"]
        db.session.commit()

        server_schema = ServerSchema()
        return_data = server_schema.dump(server).data
        return jsonify(return_data), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0')