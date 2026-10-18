export interface SelectedDOMElement {
  type: 'dom';
  tagName: string;
  id?: string;
  className?: string;
  componentHint?: string;
  textContent?: string;
  selector: string;
  href?: string;
  src?: string;
  alt?: string;
  ariaLabel?: string;
  size?: { width: number; height: number };
  styles?: Partial<Record<'color' | 'backgroundColor' | 'fontFamily' | 'fontSize' | 'fontWeight' | 'padding' | 'margin' | 'borderRadius' | 'display', string>>;
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
