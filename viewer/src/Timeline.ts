// ABOUTME: Timeline playback engine for simulation animation.
// ABOUTME: Handles play, pause, seek, and step operations.

import { SimulationState } from './SimulationState.ts';

export type TimelineCallback = (time: number) => void;

export class Timeline {
  private state: SimulationState;
  private currentTime = 0;
  private speed = 1.0;
  private isPlaying = false;
  private lastFrameTime: number | null = null;
  private onUpdate: TimelineCallback | null = null;

  constructor(state: SimulationState) {
    this.state = state;
  }

  setOnUpdate(callback: TimelineCallback): void {
    this.onUpdate = callback;
  }

  play(): void {
    if (!this.isPlaying) {
      this.isPlaying = true;
      this.lastFrameTime = performance.now();
      this.tick();
    }
  }

  pause(): void {
    this.isPlaying = false;
    this.lastFrameTime = null;
  }

  toggle(): void {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  }

  seek(time: number): void {
    // Clamp time to valid range
    time = Math.max(0, Math.min(time, this.state.getDuration()));

    // If seeking backward, reset and replay from start
    if (time < this.currentTime) {
      this.state.reset();
      this.currentTime = 0;
    }

    // Advance to the target time
    this.state.advanceTo(time);
    this.currentTime = time;

    if (this.onUpdate) {
      this.onUpdate(this.currentTime);
    }
  }

  step(): void {
    const nextTime = this.state.getNextEventTime();
    if (nextTime !== null) {
      this.seek(nextTime);
    }
  }

  setSpeed(speed: number): void {
    this.speed = speed;
  }

  getSpeed(): number {
    return this.speed;
  }

  getCurrentTime(): number {
    return this.currentTime;
  }

  getDuration(): number {
    return this.state.getDuration();
  }

  isFinished(): boolean {
    return this.currentTime >= this.state.getDuration();
  }

  getProgress(): number {
    const duration = this.state.getDuration();
    return duration > 0 ? this.currentTime / duration : 0;
  }

  reset(): void {
    this.pause();
    this.state.reset();
    this.currentTime = 0;
    if (this.onUpdate) {
      this.onUpdate(this.currentTime);
    }
  }

  private tick = (): void => {
    if (!this.isPlaying) return;

    const now = performance.now();
    if (this.lastFrameTime !== null) {
      const deltaTime = (now - this.lastFrameTime) / 1000; // Convert to seconds
      const timeAdvance = deltaTime * this.speed;

      this.currentTime = Math.min(
        this.currentTime + timeAdvance,
        this.state.getDuration()
      );

      this.state.advanceTo(this.currentTime);

      if (this.onUpdate) {
        this.onUpdate(this.currentTime);
      }

      // Stop at end
      if (this.currentTime >= this.state.getDuration()) {
        this.pause();
        return;
      }
    }

    this.lastFrameTime = now;
    requestAnimationFrame(this.tick);
  };
}
