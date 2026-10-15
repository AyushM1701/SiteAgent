import json
import queue


def test_live_sse_keeps_typed_failure_result_at_original_depth(monkeypatch):
    import server.app as server
    from server.event_bus import EventBus
    result={'status':'blocked','blocked_sections':['hero']}
    payload=EventBus().publish('sse-terminal',{'type':'result','data':result})
    subscription=queue.Queue()
    subscription.put(payload)
    monkeypatch.setattr(server.event_bus,'subscribe',lambda *args:subscription)
    monkeypatch.setattr(server.event_bus,'unsubscribe',lambda *args:None)
    monkeypatch.setattr(server,'_get_task_result',lambda tid:None)
    monkeypatch.setitem(server.task_queues,'sse-terminal',queue.Queue())
    response=server.app.test_client().get('/api/stream/sse-terminal',buffered=False)
    try:
        chunk=next(response.response).decode()
        event=json.loads(next(line[6:] for line in chunk.splitlines() if line.startswith('data: ')))
        assert event['type']=='task.failed'
        assert event['data']['result']==result
    finally: response.close()
