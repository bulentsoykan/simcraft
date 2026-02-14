// ABOUTME: Type definitions for animation data structures.
// ABOUTME: Matches the JSON format exported by Python VisualizationRecorder.

export interface AnimationData {
  version: string;
  simulation: SimulationInfo;
  components: Record<string, ComponentInfo>;
  events: AnimationEvent[];
}

export interface SimulationInfo {
  name: string;
  duration: number;
}

export interface ComponentInfo {
  type: 'server' | 'queue';
  capacity: number;
}

export interface AnimationEvent {
  t: number;
  type: EventType;
  entity: string;
  loc?: string;
  entity_type?: string;
}

export type EventType =
  | 'entity_created'
  | 'enter_queue'
  | 'start_service'
  | 'depart'
  | 'balk';

export interface EntityState {
  id: string;
  type: string;
  location: string | null;
  status: 'created' | 'queued' | 'in_service' | 'departed' | 'balked';
  queuePosition?: number;
}

export interface ComponentLayout {
  name: string;
  type: 'server' | 'queue';
  x: number;
  y: number;
  width: number;
  height: number;
  capacity: number;
}
