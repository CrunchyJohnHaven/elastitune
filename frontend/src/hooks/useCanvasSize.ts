import { useEffect, useRef, useState } from 'react';

interface CanvasSize {
  width: number;
  height: number;
  dpr: number;
}

export function useCanvasSize(containerRef: React.RefObject<HTMLElement>): CanvasSize {
  const [size, setSize] = useState<CanvasSize>({ width: 0, height: 0, dpr: 1 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const dpr = window.devicePixelRatio || 1;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setSize({ width, height, dpr });
      }
    });

    observer.observe(el);

    // Initial size
    const rect = el.getBoundingClientRect();
    setSize({ width: rect.width, height: rect.height, dpr });

    return () => observer.disconnect();
  }, [containerRef]);

  return size;
}
