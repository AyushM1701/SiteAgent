export interface SelectedDOMElement {
  type: 'dom';
  tagName: string;
  id?: string;
  className?: string;
  componentHint?: string;
  textContent?: string;
  selector: string;
}

export interface Selected3DObject {
  type: '3d';
  name: string;
  uuid: string;
  geometryType?: string;
  materialName?: string;
  position: { x: number; y: number; z: number };
  rotation: { x: number; y: number; z: number };
  componentHint?: string;
}

export type WorkbenchSelection = SelectedDOMElement | Selected3DObject | null;
