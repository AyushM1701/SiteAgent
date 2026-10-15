import { create } from 'zustand';
import { ChatMessage, QueuedPrompt } from '../types/chat';

interface ChatStoreState {
  messages: ChatMessage[];
  queuedPrompts: QueuedPrompt[];

  addMessage: (msg: ChatMessage) => void;
  updateMessage: (id: string, partial: Partial<ChatMessage>) => void;
  addQueuedPrompt: (prompt: QueuedPrompt) => void;
  updateQueuedPrompt: (id: string, partial: Partial<QueuedPrompt>) => void;
  removeQueuedPrompt: (id: string) => void;
  promoteQueuedPrompt: (id: string, taskId: string) => void;
  clearQueuedPrompts: () => void;
  clearMessages: () => void;
  setMessages: (messages: ChatMessage[]) => void;
}

export const useChatStore = create<ChatStoreState>((set) => ({
  messages: [],
  queuedPrompts: [],

  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),

  updateMessage: (id, partial) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, ...partial } : m)),
    })),

  addQueuedPrompt: (prompt) =>
    set((state) => {
      // Also add as a chat message with role 'user' and isQueued: true
      const userMsg: ChatMessage = {
        id: prompt.id,
        role: 'user',
        content: prompt.content,
        timestamp: prompt.createdAt,
        isQueued: true,
        queuePosition: prompt.queuePosition,
        taskId: prompt.taskId,
      };
      return {
        queuedPrompts: [...state.queuedPrompts, prompt],
        messages: [...state.messages, userMsg],
      };
    }),

  updateQueuedPrompt: (id, partial) =>
    set((state) => ({
      queuedPrompts: state.queuedPrompts.map((p) => (p.id === id ? { ...p, ...partial } : p)),
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, isQueued: partial.status === 'queued', queuePosition: partial.queuePosition } : m
      ),
    })),

  removeQueuedPrompt: (id) =>
    set((state) => ({
      queuedPrompts: state.queuedPrompts.filter((p) => p.id !== id),
      messages: state.messages.filter((m) => m.id !== id),
    })),

  promoteQueuedPrompt: (id, taskId) =>
    set((state) => ({
      queuedPrompts: state.queuedPrompts.filter((p) => p.id !== id),
      messages: state.messages.map((m) =>
        m.id === id
          ? {
              ...m,
              isQueued: false,
              taskId,
            }
          : m
      ),
    })),

  clearMessages: () => set({ messages: [], queuedPrompts: [] }),
  clearQueuedPrompts: () =>
    set((state) => ({
      queuedPrompts: [],
      messages: state.messages.filter((m) => !m.isQueued),
    })),
  setMessages: (messages) => set({ messages }),
}));
