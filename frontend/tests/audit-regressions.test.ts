import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import fixture from './fixtures/workbench_audit_session_result.json';
import { loadProject } from '../src/services/session';
import { api } from '../src/services/api';
import { useAgentStore } from '../src/state/agent-store';
import { useChatStore } from '../src/state/chat-store';
import { ProjectWebSocketClient, projectWsClient } from '../src/services/project-ws';
import { TaskStreamManager } from '../src/services/sse';

vi.hoisted(() => { Object.defineProperty(window, 'matchMedia', { configurable:true, value: () => ({matches:false}) }); });

describe('workbench audit regressions', () => {
  it('project hydration cannot overwrite the active task stream callbacks', () => {
    class Socket {static OPEN=1;readyState=1;close(){}send(){} }
    vi.stubGlobal('WebSocket',Socket);
    const client=new ProjectWebSocketClient();
    const callbacks={onEvent:vi.fn(),onResult:vi.fn(),onDone:vi.fn()};
    client.connect('project',callbacks,'active-task');
    client.connect('project',{onEvent:vi.fn()});
    expect(client.getActiveTaskId()).toBe('active-task');
    expect(client.getCallbacks()).toBe(callbacks);
    client.disconnect();vi.unstubAllGlobals();
  });

  it('uses the advertised dedicated project websocket endpoint', () => {
    const urls:string[]=[];
    class Socket {static OPEN=1;readyState=1;constructor(url:string){urls.push(url);}close(){}send(){} }
    vi.stubGlobal('WebSocket',Socket);
    const client=new ProjectWebSocketClient();
    client.setEndpoint('ws://127.0.0.1:5002/ws/projects');
    client.connect('project',{onEvent:vi.fn()});
    expect(urls[0]).toBe('ws://127.0.0.1:5002/ws/projects/project?lastEventId=0');
    client.disconnect();vi.unstubAllGlobals();
  });
  beforeEach(() => {
    useAgentStore.getState().resetAgent();
    useChatStore.getState().clearMessages();
  });
  afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

  it('restores stored role-based history and the blocked result', async () => {
    vi.spyOn(api, 'getProject').mockResolvedValue(fixture as any);
    vi.spyOn(projectWsClient, 'connect').mockImplementation(() => {});
    await loadProject(fixture.session_id);
    const messages = useChatStore.getState().messages;
    expect(messages[0]?.content).toContain('Aster Objects');
    expect(messages[1]?.summary?.completionStatus).toBe('BLOCKED');
    expect(messages[1]?.summary?.validation?.build_status).toBe(fixture.history[1].validation.build_status);
    expect(messages[1]?.summary?.blockedSections).toEqual(fixture.history[1].blocked_diagnostics);
    expect(useAgentStore.getState().validationResult?.errors).toContain('[Generation blocked] shop: structural_violation');
    expect(useAgentStore.getState().status).toBe('failed');
  });

  it('keeps detailed browser validation evidence from build events', () => {
    useAgentStore.getState().applyEvent({type:'build.result',timestamp:1,data:{...fixture.last_validation, motion_runtime_status:'unverified', three_d_runtime_status:'unverified'}});
    expect(useAgentStore.getState().validationResult?.motion_runtime_status).toBe('unverified');
    expect(useAgentStore.getState().validationResult?.three_d_runtime_status).toBe('unverified');
  });

  it('uses the backend task id rather than the project id for restored SSE fallback', async () => {
    vi.spyOn(api, 'getProject').mockResolvedValue({...fixture, active_task_id:'actual-task'} as any);
    const connect = vi.spyOn(projectWsClient, 'connect').mockImplementation(() => {});
    await loadProject(fixture.session_id);
    expect(connect.mock.calls.at(-1)?.[2]).toBe('actual-task');
  });

  it('uses the outer event filename when metadata is nested', () => {
    useAgentStore.getState().applyEvent({type:'file.created',timestamp:1,path:'src/Hero.tsx',data:{chars:120}} as any);
    expect(useAgentStore.getState().currentActivities[0].title).toBe('Created src/Hero.tsx');
  });

  it('uses a task-neutral generation label', () => {
    useAgentStore.getState().setStatus('generating');
    expect(useAgentStore.getState().statusMessage).not.toContain('component');
  });

  it('falls back after five rapidly failing reconnects even when each socket opens', () => {
    vi.useFakeTimers();
    const sockets: any[] = [];
    class Socket {
      static OPEN = 1;
      readyState = 1;
      onopen: any; onclose: any; onmessage: any; onerror: any;
      constructor() { sockets.push(this); }
      close() {} send() {}
    }
    vi.stubGlobal('WebSocket', Socket);
    const client = new ProjectWebSocketClient();
    const fallback = vi.fn(() => ({disconnect: vi.fn()}));
    client.setFallbackFactory(fallback);
    client.connect('project', {onEvent:vi.fn()}, 'task');
    for (let i=0;i<6;i++) {
      const socket = sockets.at(-1);
      socket.onopen();
      socket.onclose({code:1006});
      vi.advanceTimersByTime(5000);
    }
    expect(fallback).toHaveBeenCalledOnce();
    client.disconnect();
    vi.unstubAllGlobals();
  });

  it('delivers a failed task result and stops streaming without completing it', () => {
    const sockets: any[] = [];
    class Socket {static OPEN=1; readyState=1; onmessage:any; onopen:any; onclose:any; onerror:any; constructor(){sockets.push(this);} close(){} send(){} }
    vi.stubGlobal('WebSocket', Socket);
    const client = new ProjectWebSocketClient();
    const onResult=vi.fn(), onDone=vi.fn(), onEvent=vi.fn();
    client.connect('project', {onEvent,onResult,onDone}, 'task');
    sockets[0].onmessage({data:JSON.stringify({type:'task.failed',data:{result:{status:'blocked',validation:fixture.last_validation}}})});
    expect(onResult).toHaveBeenCalledWith(expect.objectContaining({status:'blocked'}));
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({type:'task.failed'}));
    expect(onDone).toHaveBeenCalledOnce();
    client.disconnect(); vi.unstubAllGlobals();
  });

  it('does not duplicate results when a replay repeats an already delivered event', () => {
    const sockets:any[]=[];
    class Socket {static OPEN=1;readyState=1;onmessage:any;constructor(){sockets.push(this);}close(){}send(){} }
    vi.stubGlobal('WebSocket',Socket);
    const client=new ProjectWebSocketClient();
    const onResult=vi.fn();
    client.connect('project',{onEvent:vi.fn(),onResult},'task');
    const data=JSON.stringify({type:'task.completed',seq:7,data:{result:{status:'completed'}}});
    sockets[0].onmessage({data});sockets[0].onmessage({data});
    expect(onResult).toHaveBeenCalledOnce();
    expect(client.getLastEventId()).toBe(7);
    client.disconnect();vi.unstubAllGlobals();
  });

  it('SSE fallback preserves the project channel context', () => {
    class Socket {static OPEN=1;readyState=1;close(){}send(){} }
    class Source {close(){} }
    vi.stubGlobal('WebSocket',Socket); vi.stubGlobal('EventSource',Source);
    projectWsClient.connect('demo',{onEvent:vi.fn()},'task');
    const fallback = new TaskStreamManager();
    fallback.connect('task',{onEvent:vi.fn()});
    expect(projectWsClient.getProjectId()).toBe('demo');
    fallback.disconnect(); projectWsClient.disconnect(); vi.unstubAllGlobals();
  });

  it('SSE fallback hydrates the blocked result in a terminal failure', () => {
    const sources:any[]=[];
    class Source {onmessage:any;onerror:any;constructor(){sources.push(this);}close(){} }
    vi.stubGlobal('EventSource',Source);
    const onResult=vi.fn(),onDone=vi.fn(),onEvent=vi.fn();
    const fallback=new TaskStreamManager();
    fallback.connect('task',{onResult,onDone,onEvent});
    sources[0].onmessage({data:JSON.stringify({type:'task.failed',data:{result:{status:'blocked'}}})});
    expect(onResult).toHaveBeenCalledWith({status:'blocked'});
    expect(onDone).toHaveBeenCalledOnce();
    fallback.disconnect(); vi.unstubAllGlobals();
  });

  it.each(['websocket', 'sse'])('%s keeps filenames across the transport boundary', (transport) => {
    const connections:any[]=[];
    class Connection {static OPEN=1;readyState=1;onmessage:any;onopen:any;onclose:any;onerror:any;constructor(){connections.push(this);}close(){}send(){} }
    vi.stubGlobal('WebSocket',Connection); vi.stubGlobal('EventSource',Connection);
    const client=transport==='websocket' ? new ProjectWebSocketClient() : new TaskStreamManager();
    client.connect('demo',{onEvent:event=>useAgentStore.getState().applyEvent(event)});
    connections[0].onmessage({data:JSON.stringify({type:'file.created',path:'src/Shop.tsx',data:{chars:100}})});
    expect(useAgentStore.getState().currentActivities[0].title).toBe('Created src/Shop.tsx');
    client.disconnect();vi.unstubAllGlobals();
  });
});
