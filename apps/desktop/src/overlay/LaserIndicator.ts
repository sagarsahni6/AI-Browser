/**
 * LaserIndicator: Visual click feedback overlay for autonomous browser actions.
 * Renders an animated laser ripple and core dot at the exact (x, y) coordinates of clicks.
 */

let isStyleInjected = false;

function injectLaserStyles(): void {
  if (isStyleInjected || typeof document === 'undefined') return;

  const styleId = 'comet-laser-indicator-styles';
  if (document.getElementById(styleId)) {
    isStyleInjected = true;
    return;
  }

  const style = document.createElement('style');
  style.id = styleId;
  style.textContent = `
    @keyframes cometLaserCore {
      0% {
        transform: translate(-50%, -50%) scale(0.3);
        opacity: 1;
      }
      50% {
        transform: translate(-50%, -50%) scale(1.2);
        opacity: 0.9;
      }
      100% {
        transform: translate(-50%, -50%) scale(1);
        opacity: 0;
      }
    }

    @keyframes cometLaserRipple {
      0% {
        transform: translate(-50%, -50%) scale(0.2);
        opacity: 0.95;
      }
      100% {
        transform: translate(-50%, -50%) scale(2.8);
        opacity: 0;
      }
    }

    .comet-laser-container {
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 2147483647;
      overflow: hidden;
    }

    .comet-laser-wrapper {
      position: absolute;
      pointer-events: none;
    }

    .comet-laser-core {
      position: absolute;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: radial-gradient(circle, #ffffff 15%, #ef4444 80%);
      box-shadow: 0 0 12px 3px rgba(239, 68, 68, 0.9), 0 0 24px 6px rgba(239, 68, 68, 0.5);
      animation: cometLaserCore 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      pointer-events: none;
    }

    .comet-laser-ripple {
      position: absolute;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid rgba(239, 68, 68, 0.85);
      box-shadow: 0 0 10px rgba(239, 68, 68, 0.6);
      animation: cometLaserRipple 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      pointer-events: none;
    }

    .comet-laser-ripple-secondary {
      position: absolute;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 1.5px solid rgba(248, 113, 113, 0.6);
      animation: cometLaserRipple 1.0s cubic-bezier(0.16, 1, 0.3, 1) 0.1s forwards;
      pointer-events: none;
    }
  `;
  document.head.appendChild(style);
  isStyleInjected = true;
}

function getOrCreateContainer(): HTMLElement | null {
  if (typeof document === 'undefined') return null;

  let container = document.getElementById('comet-laser-overlay-root');
  if (!container) {
    container = document.createElement('div');
    container.id = 'comet-laser-overlay-root';
    container.className = 'comet-laser-container';
    document.body.appendChild(container);
  }
  return container;
}

/**
 * Display an animated laser ripple and dot at viewport coordinates (x, y).
 */
export function showLaserIndicator(x: number, y: number): void {
  if (typeof document === 'undefined') return;

  injectLaserStyles();
  const container = getOrCreateContainer();
  if (!container) return;

  const wrapper = document.createElement('div');
  wrapper.className = 'comet-laser-wrapper';
  wrapper.style.left = `${x}px`;
  wrapper.style.top = `${y}px`;

  const core = document.createElement('div');
  core.className = 'comet-laser-core';

  const ripple = document.createElement('div');
  ripple.className = 'comet-laser-ripple';

  const secondaryRipple = document.createElement('div');
  secondaryRipple.className = 'comet-laser-ripple-secondary';

  wrapper.appendChild(ripple);
  wrapper.appendChild(secondaryRipple);
  wrapper.appendChild(core);
  container.appendChild(wrapper);

  // Auto cleanup after animation finishes
  setTimeout(() => {
    wrapper.remove();
  }, 1100);
}

/**
 * Initialize the laser indicator listener on window.electronAPI.
 * Returns an unsubscription callback.
 */
export function initLaserIndicator(): () => void {
  if (typeof window === 'undefined' || !window.electronAPI?.onLaserIndicator) {
    return () => {};
  }

  const unsubscribe = window.electronAPI.onLaserIndicator((coords: { x: number; y: number }) => {
    if (coords && typeof coords.x === 'number' && typeof coords.y === 'number') {
      showLaserIndicator(coords.x, coords.y);
    }
  });

  return () => {
    unsubscribe?.();
    const container = document.getElementById('comet-laser-overlay-root');
    if (container) {
      container.remove();
    }
  };
}
