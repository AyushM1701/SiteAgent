import json
import pytest
from flask import Flask
from websockets.sync.client import connect
from websockets.exceptions import InvalidStatus
from server.project_socket import ProjectSocketServer


def test_dedicated_transport_survives_idle_and_returns_only_websocket_frames():
    app=Flask(__name__)
    def handler(ws, project):
        assert ws.receive(timeout=.05) is None
        ws.send(json.dumps({'type':'ready','project':project}))
        ws.send(ws.receive(timeout=2))
    server=ProjectSocketServer(app,handler,port=0,origins=['http://127.0.0.1:5000'])
    server.start()
    try:
        with connect(f'ws://127.0.0.1:{server.port}/ws/projects/demo',origin='http://127.0.0.1:5000') as ws:
            assert json.loads(ws.recv())['project']=='demo'
            ws.send('ping')
            assert ws.recv()=='ping'
            # A clean close must not append an HTTP 200 response to the stream.
            from websockets.exceptions import ConnectionClosedOK
            with pytest.raises(ConnectionClosedOK): ws.recv()
    finally: server.stop()


def test_dedicated_transport_rejects_untrusted_browser_origin():
    server=ProjectSocketServer(Flask(__name__),lambda *args:None,port=0,origins=['http://127.0.0.1:5000'])
    server.start()
    try:
        with pytest.raises(InvalidStatus):
            with connect(f'ws://127.0.0.1:{server.port}/ws/projects/demo',origin='https://untrusted.example'): pass
    finally: server.stop()


def test_real_project_forwarder_survives_replay_then_idle():
    import server.app as workbench
    project = 'socket-regression-replay'
    workbench.event_bus.publish(project, {'type':'status', 'status':'Generating hero'}, project_id=project)
    server = ProjectSocketServer(workbench.app, workbench._handle_project_websocket, port=0)
    server.start()
    try:
        with connect(f'ws://127.0.0.1:{server.port}/ws/projects/{project}?lastEventId=0', origin='http://127.0.0.1:5000') as ws:
            assert json.loads(ws.recv(timeout=2))['type'] == 'connection.ready'
            ws.recv(timeout=2)
            import time
            time.sleep(5)
            ws.send(json.dumps({'type':'ping'}))
            assert json.loads(ws.recv(timeout=2))['type'] == 'pong'
    finally: server.stop()


def test_inherited_http_socket_timeout_does_not_close_project_stream():
    import socket, time
    app=Flask(__name__)
    def handler(ws, project):
        ws.send('ready')
        ws.send(ws.receive(timeout=2))
    server=ProjectSocketServer(app,handler,port=0)
    server.start()
    original=socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(.1)
        with connect(f'ws://127.0.0.1:{server.port}/ws/projects/idle',origin='http://127.0.0.1:5000') as ws:
            assert ws.recv(timeout=2)=='ready'
            socket.setdefaulttimeout(original)
            time.sleep(.4)
            ws.send('still connected')
            assert ws.recv(timeout=2)=='still connected'
    finally:
        socket.setdefaulttimeout(original)
        server.stop()
