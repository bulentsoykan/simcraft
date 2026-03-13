// ABOUTME: Reconstructs simulation state from event stream.
// ABOUTME: Tracks entity positions and statuses at any point in time.

import { AnimationData, AnimationEvent, EntityState } from './types.ts';

export class SimulationState {
  private data: AnimationData;
  private entities: Map<string, EntityState> = new Map();
  private currentEventIndex = 0;
  private currentTime = 0;

  // Queue tracking: maps queue name to ordered list of entity IDs
  private queues: Map<string, string[]> = new Map();

  // Server tracking: maps server name to set of entity IDs in service
  private servers: Map<string, Set<string>> = new Map();

  constructor(data: AnimationData) {
    this.data = data;
    this.initializeComponents();
  }

  private initializeComponents(): void {
    for (const [name, info] of Object.entries(this.data.components)) {
      if (info.type === 'queue') {
        this.queues.set(name, []);
      } else if (info.type === 'server') {
        this.servers.set(name, new Set());
      }
    }
  }

  reset(): void {
    this.entities.clear();
    this.currentEventIndex = 0;
    this.currentTime = 0;

    // Reset queues and servers
    for (const queue of this.queues.values()) {
      queue.length = 0;
    }
    for (const server of this.servers.values()) {
      server.clear();
    }
  }

  advanceTo(time: number): EntityState[] {
    // Process all events up to the given time
    while (
      this.currentEventIndex < this.data.events.length &&
      this.data.events[this.currentEventIndex].t <= time
    ) {
      this.processEvent(this.data.events[this.currentEventIndex]);
      this.currentEventIndex++;
    }

    this.currentTime = time;
    return Array.from(this.entities.values());
  }

  private processEvent(event: AnimationEvent): void {
    switch (event.type) {
      case 'entity_created':
        this.entities.set(event.entity, {
          id: event.entity,
          type: event.entity_type || 'Entity',
          location: null,
          status: 'created',
        });
        break;

      case 'enter_queue':
        this.handleEnterQueue(event);
        break;

      case 'start_service':
        this.handleStartService(event);
        break;

      case 'depart':
        this.handleDepart(event);
        break;

      case 'balk':
        this.handleBalk(event);
        break;
    }
  }

  private handleEnterQueue(event: AnimationEvent): void {
    const entity = this.entities.get(event.entity);
    if (!entity || !event.loc) return;

    // Remove from previous queue if any
    this.removeFromQueue(event.entity);

    // Add to new queue
    const queue = this.queues.get(event.loc);
    if (queue) {
      queue.push(event.entity);
      entity.location = event.loc;
      entity.status = 'queued';
      entity.queuePosition = queue.length - 1;
    }
  }

  private handleStartService(event: AnimationEvent): void {
    const entity = this.entities.get(event.entity);
    if (!entity || !event.loc) return;

    // Remove from queue if was queued
    this.removeFromQueue(event.entity);

    // Add to server
    const server = this.servers.get(event.loc);
    if (server) {
      server.add(event.entity);
      entity.location = event.loc;
      entity.status = 'in_service';
      delete entity.queuePosition;
    }
  }

  private handleDepart(event: AnimationEvent): void {
    const entity = this.entities.get(event.entity);
    if (!entity || !event.loc) return;

    // Remove from server
    const server = this.servers.get(event.loc);
    if (server) {
      server.delete(event.entity);
    }

    entity.location = 'exit';
    entity.status = 'departed';
  }

  private handleBalk(event: AnimationEvent): void {
    const entity = this.entities.get(event.entity);
    if (!entity) return;

    entity.location = 'exit';
    entity.status = 'balked';
  }

  private removeFromQueue(entityId: string): void {
    for (const queue of this.queues.values()) {
      const index = queue.indexOf(entityId);
      if (index !== -1) {
        queue.splice(index, 1);
        // Update queue positions for remaining entities
        for (let i = index; i < queue.length; i++) {
          const e = this.entities.get(queue[i]);
          if (e) {
            e.queuePosition = i;
          }
        }
        return;
      }
    }
  }

  getEntities(): EntityState[] {
    return Array.from(this.entities.values());
  }

  getEntity(id: string): EntityState | undefined {
    return this.entities.get(id);
  }

  getQueueContents(queueName: string): string[] {
    return this.queues.get(queueName) || [];
  }

  getServerContents(serverName: string): string[] {
    const server = this.servers.get(serverName);
    return server ? Array.from(server) : [];
  }

  getCurrentTime(): number {
    return this.currentTime;
  }

  getDuration(): number {
    return this.data.simulation.duration;
  }

  getEventCount(): number {
    return this.data.events.length;
  }

  getNextEventTime(): number | null {
    if (this.currentEventIndex < this.data.events.length) {
      return this.data.events[this.currentEventIndex].t;
    }
    return null;
  }

  getData(): AnimationData {
    return this.data;
  }
}
