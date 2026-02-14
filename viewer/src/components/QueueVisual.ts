// ABOUTME: Visual representation of a queue component.
// ABOUTME: Renders as a horizontal line of waiting positions.

import * as THREE from 'three';
import { ComponentLayout } from '../types.ts';

export class QueueVisual extends THREE.Group {
  private layout: ComponentLayout;
  private background!: THREE.Mesh;
  private label!: THREE.Sprite;
  private maxVisibleSlots = 10;

  // Visual constants
  private static readonly SLOT_SIZE = 25;
  private static readonly SLOT_GAP = 8;
  private static readonly PADDING = 10;
  private static readonly COLORS = {
    background: 0x0f3460,
    border: 0x16213e,
    label: '#888',
  };

  constructor(layout: ComponentLayout) {
    super();
    this.layout = layout;

    this.createBackground();
    this.createLabel();

    this.position.set(layout.x, layout.y, 0);
  }

  private createBackground(): void {
    const width = this.calculateWidth();
    const height = QueueVisual.SLOT_SIZE + QueueVisual.PADDING * 2;

    // Create rounded rectangle shape
    const shape = this.createRoundedRectShape(width, height, 6);
    const geometry = new THREE.ShapeGeometry(shape);

    const material = new THREE.MeshBasicMaterial({
      color: QueueVisual.COLORS.background,
      transparent: true,
      opacity: 0.5,
    });

    this.background = new THREE.Mesh(geometry, material);
    this.background.position.set(0, 0, -0.5);
    this.add(this.background);

    // Store dimensions for layout
    this.layout.width = width;
    this.layout.height = height;
  }

  private createLabel(): void {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d')!;
    canvas.width = 256;
    canvas.height = 64;

    context.fillStyle = QueueVisual.COLORS.label;
    context.font = '18px sans-serif';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText('Queue', 128, 32);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture });
    this.label = new THREE.Sprite(material);
    this.label.scale.set(60, 15, 1);
    this.label.position.set(0, -30, 1);
    this.add(this.label);
  }

  private calculateWidth(): number {
    return (
      this.maxVisibleSlots * QueueVisual.SLOT_SIZE +
      (this.maxVisibleSlots - 1) * QueueVisual.SLOT_GAP +
      QueueVisual.PADDING * 2
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

  getPositionForIndex(index: number): THREE.Vector3 {
    // Queue positions go from right to left (first in queue is closest to server)
    const startX = (this.maxVisibleSlots - 1) * (QueueVisual.SLOT_SIZE + QueueVisual.SLOT_GAP) / 2;
    const x = startX - index * (QueueVisual.SLOT_SIZE + QueueVisual.SLOT_GAP);

    const worldPos = new THREE.Vector3(x, 0, 0);
    worldPos.add(this.position);
    return worldPos;
  }

  getWidth(): number {
    return this.layout.width;
  }
}
