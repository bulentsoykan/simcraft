// ABOUTME: Three.js 2D scene setup with orthographic camera.
// ABOUTME: Handles rendering, resize, and coordinate system.

import * as THREE from 'three';

export class Scene {
  private scene: THREE.Scene;
  private camera: THREE.OrthographicCamera;
  private renderer: THREE.WebGLRenderer;
  private container: HTMLElement;

  // World bounds for auto-fitting
  private worldHeight = 600;

  constructor(container: HTMLElement) {
    this.container = container;

    // Create scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1a1a2e);

    // Create orthographic camera for 2D view
    const aspect = container.clientWidth / container.clientHeight;
    const halfHeight = this.worldHeight / 2;
    const halfWidth = halfHeight * aspect;

    this.camera = new THREE.OrthographicCamera(
      -halfWidth,
      halfWidth,
      halfHeight,
      -halfHeight,
      0.1,
      1000
    );
    this.camera.position.z = 100;

    // Create renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(this.renderer.domElement);

    // Handle resize
    window.addEventListener('resize', () => this.onResize());

    // Add grid for visual reference
    this.addGrid();
  }

  private addGrid(): void {
    const gridHelper = new THREE.GridHelper(800, 20, 0x0f3460, 0x0f3460);
    gridHelper.rotation.x = Math.PI / 2;
    gridHelper.position.z = -1;
    this.scene.add(gridHelper);
  }

  private onResize(): void {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;

    const aspect = width / height;
    const halfHeight = this.worldHeight / 2;
    const halfWidth = halfHeight * aspect;

    this.camera.left = -halfWidth;
    this.camera.right = halfWidth;
    this.camera.top = halfHeight;
    this.camera.bottom = -halfHeight;
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(width, height);
  }

  add(object: THREE.Object3D): void {
    this.scene.add(object);
  }

  remove(object: THREE.Object3D): void {
    this.scene.remove(object);
  }

  clear(): void {
    // Remove all objects except the grid
    const toRemove: THREE.Object3D[] = [];
    this.scene.traverse((obj) => {
      if (obj !== this.scene && !(obj instanceof THREE.GridHelper)) {
        toRemove.push(obj);
      }
    });
    toRemove.forEach((obj) => {
      if (obj.parent) {
        obj.parent.remove(obj);
      }
    });
  }

  render(): void {
    this.renderer.render(this.scene, this.camera);
  }

  getScene(): THREE.Scene {
    return this.scene;
  }

  getCamera(): THREE.OrthographicCamera {
    return this.camera;
  }
}
