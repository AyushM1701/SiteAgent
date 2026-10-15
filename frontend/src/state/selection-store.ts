import { create } from 'zustand';
import { SelectedDOMElement, Selected3DObject } from '../types/selection';

interface SelectionStoreState {
  selectedElement: SelectedDOMElement | null;
  selected3DObject: Selected3DObject | null;
  inspectMode: 'none' | 'dom' | '3d';

  setSelectedElement: (el: SelectedDOMElement | null) => void;
  setSelected3DObject: (obj: Selected3DObject | null) => void;
  setInspectMode: (mode: 'none' | 'dom' | '3d') => void;
  clearSelection: () => void;
}

export const useSelectionStore = create<SelectionStoreState>((set) => ({
  selectedElement: null,
  selected3DObject: null,
  inspectMode: 'none',

  setSelectedElement: (el) => set({ selectedElement: el, selected3DObject: null }),
  setSelected3DObject: (obj) => set({ selected3DObject: obj, selectedElement: null }),
  setInspectMode: (mode) => set({ inspectMode: mode }),
  clearSelection: () => set({ selectedElement: null, selected3DObject: null, inspectMode: 'none' }),
}));
