import sys
import zmq
import simplejson as json
import requests


from ndansibase import ansi_runner

api_server_url = "http://api.nd.devilstops.in"
port = "5560"
# Socket to talk to server
context = zmq.Context()
socket = context.socket(zmq.SUB)
print "Collecting updates from server..."
socket.connect ("tcp://localhost:%s" % port)
topicfilter = "netdata"
socket.setsockopt(zmq.SUBSCRIBE, topicfilter)


while True:
    payload = socket.recv()
    topic, message = (topicfilter, payload.lstrip(topicfilter).strip())#payload.split()

    json_message = json.loads(message)
    sid = json_message["sid"]
    server_name = json_message["server_name"]
    server_ip = json_message["server_ip"]

    if ansi_runner(server_name, server_ip, "netdata", connection='ssh', become=True):
        run_result = ansi_runner(server_name, server_ip, "nginx", connection='local', become=True)
    else:
        run_result = False

    headers = {
        'content-type': "application/json",
        'cache-control': "no-cache"
        }

    if run_result:
        payload = { 'status': 'completed' }
    else:
        payload = { 'status': 'failed' }

    url = "{0}/servers/{1}".format(api_server_url, sid)
    requests.put(url, headers=headers, data=json.dumps(payload))
