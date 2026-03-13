// ABOUTME: Main entry point for the SimCraft visualization viewer.
// ABOUTME: Coordinates scene, components, and playback controls.

import * as THREE from 'three';
import { Scene } from './Scene.ts';
import { SimulationState } from './SimulationState.ts';
import { Timeline } from './Timeline.ts';
import { ServerVisual } from './components/ServerVisual.ts';
import { QueueVisual } from './components/QueueVisual.ts';
import { EntityVisual } from './components/EntityVisual.ts';
import { AnimationData, ComponentLayout, EntityState } from './types.ts';

class Viewer {
  private scene: Scene;
  private state: SimulationState | null = null;
  private timeline: Timeline | null = null;

  // Visual components
  private serverVisuals: Map<string, ServerVisual> = new Map();
  private queueVisuals: Map<string, QueueVisual> = new Map();
  private entityVisuals: Map<string, EntityVisual> = new Map();

  // Layout constants
  private static readonly COMPONENT_GAP = 180;
  private static readonly EXIT_OFFSET = 150;

  // DOM elements
  private playBtn: HTMLButtonElement;
  private stepBtn: HTMLButtonElement;
  private timelineSlider: HTMLInputElement;
  private timeDisplay: HTMLElement;
  private speedSelect: HTMLSelectElement;
  private simInfo: HTMLElement;

  constructor() {
    const container = document.getElementById('canvas-container')!;
    this.scene = new Scene(container);

    // Get DOM elements
    this.playBtn = document.getElementById('play-btn') as HTMLButtonElement;
    this.stepBtn = document.getElementById('step-btn') as HTMLButtonElement;
    this.timelineSlider = document.getElementById('timeline') as HTMLInputElement;
    this.timeDisplay = document.getElementById('time-display')!;
    this.speedSelect = document.getElementById('speed') as HTMLSelectElement;
    this.simInfo = document.getElementById('sim-info')!;

    this.setupEventListeners();
    this.animate();
  }

  private setupEventListeners(): void {
    // File input
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    fileInput.addEventListener('change', (e) => this.handleFileLoad(e));

    // Playback controls
    this.playBtn.addEventListener('click', () => this.togglePlay());
    this.stepBtn.addEventListener('click', () => this.step());

    this.timelineSlider.addEventListener('input', () => {
      if (this.timeline) {
        const progress = parseFloat(this.timelineSlider.value) / 100;
        const time = progress * this.timeline.getDuration();
        this.timeline.seek(time);
        this.updateVisuals();
      }
    });

    this.speedSelect.addEventListener('change', () => {
      if (this.timeline) {
        this.timeline.setSpeed(parseFloat(this.speedSelect.value));
      }
    });
  }

  private async handleFileLoad(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data: AnimationData = JSON.parse(text);
      this.loadAnimation(data);
    } catch (error) {
      console.error('Failed to load animation file:', error);
      alert('Failed to load animation file. Please check the console for details.');
    }
  }

  private loadAnimation(data: AnimationData): void {
    // Clear previous state
    this.clearVisuals();

    // Create new state and timeline
    this.state = new SimulationState(data);
    this.timeline = new Timeline(this.state);
    this.timeline.setOnUpdate((time) => this.onTimeUpdate(time));

    // Create component visuals with auto-layout
    this.createComponentVisuals(data);

    // Enable controls
    this.playBtn.disabled = false;
    this.stepBtn.disabled = false;
    this.timelineSlider.disabled = false;
    this.timelineSlider.max = '100';
    this.timelineSlider.value = '0';

    // Update info display
    this.simInfo.innerHTML = `
      <strong>${data.simulation.name}</strong><br>
      Duration: ${data.simulation.duration.toFixed(2)}<br>
      Events: ${data.events.length}
    `;

    // Initial render
    this.updateVisuals();
  }

  private createComponentVisuals(data: AnimationData): void {
    // Group components by server (server + its queue)
    const serverNames: string[] = [];
    const queueNames: string[] = [];

    for (const [name, info] of Object.entries(data.components)) {
      if (info.type === 'server') {
        serverNames.push(name);
      } else if (info.type === 'queue') {
        queueNames.push(name);
      }
    }

    // Layout: queues on left, servers in center, exit on right
    let xOffset = -200;

    for (const serverName of serverNames) {
      const queueName = `${serverName}.queue`;
      const serverInfo = data.components[serverName];
      const queueInfo = data.components[queueName];

      // Create queue visual
      if (queueInfo) {
        const queueLayout: ComponentLayout = {
          name: queueName,
          type: 'queue',
          x: xOffset,
          y: 0,
          width: 0,
          height: 0,
          capacity: queueInfo.capacity,
        };
        const queueVisual = new QueueVisual(queueLayout);
        this.queueVisuals.set(queueName, queueVisual);
        this.scene.add(queueVisual);

        xOffset += queueVisual.getWidth() / 2 + Viewer.COMPONENT_GAP / 2;
      }

      // Create server visual
      const serverLayout: ComponentLayout = {
        name: serverName,
        type: 'server',
        x: xOffset,
        y: 0,
        width: 0,
        height: 0,
        capacity: serverInfo.capacity,
      };
      const serverVisual = new ServerVisual(serverLayout);
      this.serverVisuals.set(serverName, serverVisual);
      this.scene.add(serverVisual);

      xOffset += Viewer.COMPONENT_GAP;
    }
  }

  private clearVisuals(): void {
    for (const visual of this.serverVisuals.values()) {
      this.scene.remove(visual);
    }
    for (const visual of this.queueVisuals.values()) {
      this.scene.remove(visual);
    }
    for (const visual of this.entityVisuals.values()) {
      this.scene.remove(visual);
    }

    this.serverVisuals.clear();
    this.queueVisuals.clear();
    this.entityVisuals.clear();
  }

  private togglePlay(): void {
    if (!this.timeline) return;

    if (this.timeline.isFinished()) {
      this.timeline.reset();
    }

    this.timeline.toggle();
    this.playBtn.textContent = this.timeline.getProgress() < 1 &&
      this.timeline.getCurrentTime() > 0 ? 'Pause' : 'Play';
  }

  private step(): void {
    if (this.timeline) {
      this.timeline.step();
      this.updateVisuals();
    }
  }

  private onTimeUpdate(time: number): void {
    // Update timeline slider
    if (this.timeline) {
      const progress = this.timeline.getProgress() * 100;
      this.timelineSlider.value = progress.toString();
    }

    // Update time display
    this.timeDisplay.textContent = `t = ${time.toFixed(2)}`;

    // Update play button text
    if (this.timeline?.isFinished()) {
      this.playBtn.textContent = 'Replay';
    }

    // Update visuals
    this.updateVisuals();
  }

  private updateVisuals(): void {
    if (!this.state) return;

    const entities = this.state.getEntities();

    // Track which entities we've seen this frame
    const seenEntities = new Set<string>();

    for (const entityState of entities) {
      seenEntities.add(entityState.id);

      let visual = this.entityVisuals.get(entityState.id);

      if (!visual) {
        // Create new entity visual
        visual = new EntityVisual(entityState);
        this.entityVisuals.set(entityState.id, visual);
        this.scene.add(visual);
      } else {
        visual.updateState(entityState);
      }

      // Update position based on state
      const targetPos = this.getEntityPosition(entityState);
      if (targetPos) {
        visual.setTargetPosition(targetPos);
      }
    }

    // Remove departed entities that have faded
    for (const [id, visual] of this.entityVisuals) {
      if (!seenEntities.has(id)) {
        this.scene.remove(visual);
        this.entityVisuals.delete(id);
      }
    }

    // Update server slot colors
    for (const [serverName, serverVisual] of this.serverVisuals) {
      serverVisual.reset();
      const contents = this.state.getServerContents(serverName);
      contents.forEach((_, index) => {
        serverVisual.occupySlot(index);
      });
    }
  }

  private getEntityPosition(state: EntityState): THREE.Vector3 | null {
    if (state.status === 'departed' || state.status === 'balked') {
      // Exit position - to the right of the last server
      let maxX = 0;
      for (const serverVisual of this.serverVisuals.values()) {
        maxX = Math.max(maxX, serverVisual.position.x);
      }
      return new THREE.Vector3(maxX + Viewer.EXIT_OFFSET, 0, 0);
    }

    if (state.status === 'in_service' && state.location) {
      const serverVisual = this.serverVisuals.get(state.location);
      if (serverVisual) {
        // Find slot for this entity
        const contents = this.state!.getServerContents(state.location);
        const slotIndex = contents.indexOf(state.id);
        if (slotIndex !== -1) {
          return serverVisual.getSlotPosition(slotIndex);
        }
        return serverVisual.position.clone();
      }
    }

    if (state.status === 'queued' && state.location) {
      const queueVisual = this.queueVisuals.get(state.location);
      if (queueVisual && state.queuePosition !== undefined) {
        return queueVisual.getPositionForIndex(state.queuePosition);
      }
    }

    // Default: spawn position (off-screen left)
    return new THREE.Vector3(-400, 0, 0);
  }

  private animate = (): void => {
    requestAnimationFrame(this.animate);

    // Update entity animations
    for (const visual of this.entityVisuals.values()) {
      visual.update(1 / 60); // Assume 60fps
    }

    this.scene.render();
  };
}

// Initialize viewer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new Viewer();
});
