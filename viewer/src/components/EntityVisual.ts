// ABOUTME: Visual representation of an entity (customer/job).
// ABOUTME: Renders as a colored circle that animates between positions.

import * as THREE from 'three';
import { EntityState } from '../types.ts';

export class EntityVisual extends THREE.Group {
  private state: EntityState;
  private circle!: THREE.Mesh;
  private targetPosition: THREE.Vector3 | null = null;
  private animationSpeed = 5;

  // Visual constants
  private static readonly RADIUS = 10;
  private static readonly COLORS = {
    created: 0x888888,
    queued: 0xf39c12,
    in_service: 0x4ecca3,
    departed: 0x4ecca3,
    balked: 0xe94560,
  };

  constructor(state: EntityState) {
    super();
    this.state = state;

    this.createCircle();
  }

  private createCircle(): void {
    const geometry = new THREE.CircleGeometry(EntityVisual.RADIUS, 32);
    const material = new THREE.MeshBasicMaterial({
      color: this.getColorForStatus(),
    });
    this.circle = new THREE.Mesh(geometry, material);
    this.circle.position.z = 2;
    this.add(this.circle);
  }

  private getColorForStatus(): number {
    return EntityVisual.COLORS[this.state.status] || EntityVisual.COLORS.created;
  }

  updateState(newState: EntityState): void {
    this.state = newState;
    const material = this.circle.material as THREE.MeshBasicMaterial;
    material.color.setHex(this.getColorForStatus());

    // Handle departed state with fade out
    if (newState.status === 'departed') {
      material.transparent = true;
      material.opacity = 0.5;
    }
  }

  setTargetPosition(target: THREE.Vector3): void {
    this.targetPosition = target.clone();
  }

  update(deltaTime: number): boolean {
    if (!this.targetPosition) {
      return false;
    }

    const distance = this.position.distanceTo(this.targetPosition);
    if (distance < 0.5) {
      this.position.copy(this.targetPosition);
      this.targetPosition = null;
      return false;
    }

    // Smooth interpolation toward target
    const step = Math.min(1, this.animationSpeed * deltaTime);
    this.position.lerp(this.targetPosition, step);
    return true;
  }

  getId(): string {
    return this.state.id;
  }

  getState(): EntityState {
    return this.state;
  }

  fadeOut(): void {
    const material = this.circle.material as THREE.MeshBasicMaterial;
    material.transparent = true;
  }
}
