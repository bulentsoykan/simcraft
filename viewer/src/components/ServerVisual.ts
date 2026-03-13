// ABOUTME: Visual representation of a server component.
// ABOUTME: Renders as a rounded rectangle with capacity slots.

import * as THREE from 'three';
import { ComponentLayout } from '../types.ts';

export class ServerVisual extends THREE.Group {
  private layout: ComponentLayout;
  private background!: THREE.Mesh;
  private slots: THREE.Mesh[] = [];
  private label!: THREE.Sprite;
  private occupiedSlots: Set<number> = new Set();

  // Visual constants
  private static readonly SLOT_SIZE = 30;
  private static readonly SLOT_GAP = 10;
  private static readonly PADDING = 15;
  private static readonly COLORS = {
    background: 0x16213e,
    border: 0x0f3460,
    slotEmpty: 0x1a1a2e,
    slotOccupied: 0x4ecca3,
    label: '#e94560',
  };

  constructor(layout: ComponentLayout) {
    super();
    this.layout = layout;

    this.createBackground();
    this.createSlots();
    this.createLabel();

    this.position.set(layout.x, layout.y, 0);
  }

  private createBackground(): void {
    const width = this.calculateWidth();
    const height = ServerVisual.SLOT_SIZE + ServerVisual.PADDING * 2;

    // Create rounded rectangle shape
    const shape = this.createRoundedRectShape(width, height, 8);
    const geometry = new THREE.ShapeGeometry(shape);

    const material = new THREE.MeshBasicMaterial({
      color: ServerVisual.COLORS.background,
    });

    this.background = new THREE.Mesh(geometry, material);
    this.background.position.set(0, 0, 0);
    this.add(this.background);

    // Add border
    const borderGeometry = new THREE.EdgesGeometry(geometry);
    const borderMaterial = new THREE.LineBasicMaterial({
      color: ServerVisual.COLORS.border,
    });
    const border = new THREE.LineSegments(borderGeometry, borderMaterial);
    this.add(border);

    // Store dimensions for layout
    this.layout.width = width;
    this.layout.height = height;
  }

  private createSlots(): void {
    const capacity = Math.max(1, this.layout.capacity);
    const startX = -((capacity - 1) * (ServerVisual.SLOT_SIZE + ServerVisual.SLOT_GAP)) / 2;

    for (let i = 0; i < capacity; i++) {
      const geometry = new THREE.CircleGeometry(ServerVisual.SLOT_SIZE / 2 - 2, 32);
      const material = new THREE.MeshBasicMaterial({
        color: ServerVisual.COLORS.slotEmpty,
      });
      const slot = new THREE.Mesh(geometry, material);

      slot.position.set(
        startX + i * (ServerVisual.SLOT_SIZE + ServerVisual.SLOT_GAP),
        0,
        1
      );
      this.slots.push(slot);
      this.add(slot);
    }
  }

  private createLabel(): void {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d')!;
    canvas.width = 256;
    canvas.height = 64;

    context.fillStyle = ServerVisual.COLORS.label;
    context.font = 'bold 24px sans-serif';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(this.layout.name, 128, 32);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture });
    this.label = new THREE.Sprite(material);
    this.label.scale.set(80, 20, 1);
    this.label.position.set(0, -40, 1);
    this.add(this.label);
  }

  private calculateWidth(): number {
    const capacity = Math.max(1, this.layout.capacity);
    return (
      capacity * ServerVisual.SLOT_SIZE +
      (capacity - 1) * ServerVisual.SLOT_GAP +
      ServerVisual.PADDING * 2
    );
  }

  private createRoundedRectShape(
    width: number,
    height: number,
    radius: number
  ): THREE.Shape {
    const shape = new THREE.Shape();
    const x = -width / 2;
    const y = -height / 2;

    shape.moveTo(x + radius, y);
    shape.lineTo(x + width - radius, y);
    shape.quadraticCurveTo(x + width, y, x + width, y + radius);
    shape.lineTo(x + width, y + height - radius);
    shape.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    shape.lineTo(x + radius, y + height);
    shape.quadraticCurveTo(x, y + height, x, y + height - radius);
    shape.lineTo(x, y + radius);
    shape.quadraticCurveTo(x, y, x + radius, y);

    return shape;
  }

  occupySlot(slotIndex: number): void {
    if (slotIndex >= 0 && slotIndex < this.slots.length) {
      this.occupiedSlots.add(slotIndex);
      const material = this.slots[slotIndex].material as THREE.MeshBasicMaterial;
      material.color.setHex(ServerVisual.COLORS.slotOccupied);
    }
  }

  releaseSlot(slotIndex: number): void {
    if (slotIndex >= 0 && slotIndex < this.slots.length) {
      this.occupiedSlots.delete(slotIndex);
      const material = this.slots[slotIndex].material as THREE.MeshBasicMaterial;
      material.color.setHex(ServerVisual.COLORS.slotEmpty);
    }
  }

  getNextAvailableSlot(): number {
    for (let i = 0; i < this.slots.length; i++) {
      if (!this.occupiedSlots.has(i)) {
        return i;
      }
    }
    return -1;
  }

  getSlotPosition(slotIndex: number): THREE.Vector3 {
    if (slotIndex >= 0 && slotIndex < this.slots.length) {
      const worldPos = new THREE.Vector3();
      this.slots[slotIndex].getWorldPosition(worldPos);
      return worldPos;
    }
    return this.position.clone();
  }

  getOccupiedCount(): number {
    return this.occupiedSlots.size;
  }

  reset(): void {
    this.occupiedSlots.clear();
    this.slots.forEach((slot) => {
      const material = slot.material as THREE.MeshBasicMaterial;
      material.color.setHex(ServerVisual.COLORS.slotEmpty);
    });
  }
}
