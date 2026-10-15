"""Project WebSockets in the model process, outside the WSGI response lifecycle."""
import re
import threading
from urllib.parse import urlsplit, unquote
from websockets.sync.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosedOK


class _ConnectionAdapter:
    def __init__(self, connection):
        self.connection = connection

    def send(self, data):
        self.connection.send(data)

    def receive(self, timeout=None):
        try:
            return self.connection.recv(timeout=timeout)
        except TimeoutError:
            return None
        except ConnectionClosedOK:
            raise
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Project socket receive stopped; transport cause: %r', getattr(self.connection, 'recv_exc', None))
            raise

    def close(self):
        self.connection.close()


class ProjectSocketServer:
    def __init__(self, app, handler, host='127.0.0.1', port=5002, origins=None):
        self.app, self.handler = app, handler
        self.host, self.port = host, port
        self.origins = origins or ['http://127.0.0.1:5000', 'http://localhost:5000']
        self.server = None
        self.thread = None

    @property
    def ready(self):
        return bool(self.thread and self.thread.is_alive())

    def _check_request(self, connection, request):
        path = urlsplit(request.path).path
        if not re.fullmatch(r'/ws/(?:projects|sessions)/[A-Za-z0-9_-]+', path):
            return connection.respond(404, 'Unknown project socket route')
        origin = request.headers.get('Origin')
        if origin and origin.rstrip('/') not in self.origins:
            return connection.respond(403, 'Untrusted workbench origin')

    def _handle(self, connection):
        path = urlsplit(connection.request.path)
        project_id = unquote(path.path.rsplit('/', 1)[-1])
        origin = connection.request.headers.get('Origin')
        # Validation and dispatch still use the existing Flask handlers and the
        # same EventBus and serialized GPU owner. No second model is loaded.
        base_url = origin or self.origins[0]
        headers = {'Origin': origin} if origin else {}
        try:
            with self.app.test_request_context(connection.request.path, base_url=base_url, headers=headers):
                self.handler(_ConnectionAdapter(connection), project_id)
        except Exception:
            self.app.logger.exception('Project socket handler failed for %s', project_id)
            connection.close(code=1011, reason='Project stream failed')

    def start(self):
        if self.ready:
            return
        def create_connection(sock, protocol, **kwargs):
            # HTTP/asset libraries may set a process-wide default socket timeout.
            # Long-lived streams must use WebSocket ping/close deadlines instead.
            sock.settimeout(None)
            return ServerConnection(sock, protocol, **kwargs)
        self.server = serve(self._handle, self.host, self.port, process_request=self._check_request, create_connection=create_connection,
                            compression=None, ping_interval=20, ping_timeout=20, max_size=1024*1024)
        self.port = self.server.socket.getsockname()[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name='project-websocket-server')
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
        if self.thread:
            self.thread.join(timeout=2)
        self.thread = None
        self.server = None
