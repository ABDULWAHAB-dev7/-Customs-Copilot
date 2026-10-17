"use client";

import { useEffect, useRef, type CSSProperties } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import { preloadSequence } from "@/lib/preloadSequence";

gsap.registerPlugin(ScrollTrigger);

export type SequenceCaption = {
  kicker: string;
  title: string;
  body: string;
};

type FrameSequenceProps = {
  frameUrl?: (index: number) => string;
  framePattern?: string;
  count: number;
  captions: readonly SequenceCaption[];
  ariaLabel: string;
  pinVh?: number;
  focalX?: number;
  focalY?: number;
};

const FADE_MAX = 0.06;

function fillPattern(pattern: string, index: number) {
  return pattern.replace(/\{n(\d*)\}/, (_, width: string) =>
    String(index + 1).padStart(Number(width) || 1, "0"),
  );
}

export default function FrameSequence({
  frameUrl,
  framePattern,
  count,
  captions,
  ariaLabel,
  pinVh = 400,
  focalX = 0.5,
  focalY = 0.5,
}: FrameSequenceProps) {
  const trackRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const loaderRef = useRef<HTMLParagraphElement>(null);
  const captionRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const track = trackRef.current;
    const stage = stageRef.current;
    const canvas = canvasRef.current;
    const loader = loaderRef.current;
    if (!track || !stage || !canvas || !loader) return;

    const context = canvas.getContext("2d");
    if (!context) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) track.classList.add("is-static");

    const frames: (HTMLImageElement | undefined)[] = new Array(count);
    let loadedCount = 0;
    let failedCount = 0;
    let cancelled = false;
    let requested = reduceMotion ? Math.floor(count / 2) : 0;

    function nearestLoaded(index: number): number {
      if (frames[index]) return index;
      for (let d = 1; d < count; d++) {
        if (index - d >= 0 && frames[index - d]) return index - d;
        if (index + d < count && frames[index + d]) return index + d;
      }
      return -1;
    }

    function paint() {
      const index = nearestLoaded(requested);
      if (index === -1) return;
      const image = frames[index];
      if (!image) return;
      const cw = canvas!.width;
      const ch = canvas!.height;
      const scale = Math.max(cw / image.naturalWidth, ch / image.naturalHeight);
      const dw = image.naturalWidth * scale;
      const dh = image.naturalHeight * scale;
      context!.clearRect(0, 0, cw, ch);
      context!.drawImage(image, (cw - dw) * focalX, (ch - dh) * focalY, dw, dh);
      canvas!.dataset.frame = String(index);
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.round(canvas!.clientWidth * dpr));
      const height = Math.max(1, Math.round(canvas!.clientHeight * dpr));
      if (canvas!.width !== width || canvas!.height !== height) {
        canvas!.width = width;
        canvas!.height = height;
        paint();
      }
    }

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    resize();

    const urlFor = frameUrl ?? ((i: number) => fillPattern(framePattern ?? "", i));
    preloadSequence(
      Array.from({ length: count }, (_, i) => urlFor(i)),
      {
        isCancelled: () => cancelled,
        onFrame(index, image) {
          frames[index] = image;
          loadedCount++;
          if (index === requested || canvas!.dataset.frame === undefined) paint();
          updateLoader();
        },
        onError() {
          failedCount++;
          updateLoader();
        },
      },
    );

    function updateLoader() {
      if (loadedCount + failedCount >= count) {
        loader!.dataset.done = "true";
        loader!.textContent = failedCount ? `${failedCount} frame(s) missing` : "";
        return;
      }
      loader!.textContent = `Loading ${loadedCount} / ${count}`;
    }
    updateLoader();

    const captionEls = captionRefs.current.filter(
      (el): el is HTMLDivElement => el !== null,
    );

    if (reduceMotion) {
      return () => {
        cancelled = true;
        resizeObserver.disconnect();
      };
    }

    const lenis = new Lenis({ duration: 1.2, smoothWheel: true });
    lenis.on("scroll", ScrollTrigger.update);
    const tick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);

    const ctx = gsap.context(() => {
      const windowSize = 1 / captionEls.length;
      const fade = Math.min(FADE_MAX, windowSize * 0.25);

      const timeline = gsap.timeline({
        scrollTrigger: {
          trigger: track,
          start: "top top",
          end: "bottom bottom",
          scrub: true,
          onUpdate: (self) => {
            const index = Math.min(count - 1, Math.round(self.progress * (count - 1)));
            if (index !== requested) {
              requested = index;
              paint();
            }
          },
        },
      });

      captionEls.forEach((el, k) => {
        const start = k * windowSize;
        const end = start + windowSize;
        if (k === 0) {
          gsap.set(el, { autoAlpha: 1, y: 0 });
        } else {
          timeline.fromTo(
            el,
            { autoAlpha: 0, y: 28 },
            { autoAlpha: 1, y: 0, duration: fade, ease: "power2.out" },
            start,
          );
        }
        if (k < captionEls.length - 1) {
          timeline.to(el, { autoAlpha: 0, y: -18, duration: fade, ease: "power2.in" }, end - fade);
        }
      });
      timeline.set({}, {}, 1);

      ScrollTrigger.create({
        trigger: track,
        start: "top top",
        end: "bottom bottom",
        pin: stage,
        pinSpacing: false,
      });
    }, track);

    return () => {
      cancelled = true;
      ctx.revert();
      gsap.ticker.remove(tick);
      lenis.destroy();
      resizeObserver.disconnect();
    };
  }, [count, frameUrl, framePattern, captions.length, focalX, focalY]);

  return (
    <section
      ref={trackRef}
      className="seq-track"
      style={{ "--pin": pinVh } as CSSProperties}
      aria-label={ariaLabel}
    >
      <div ref={stageRef} className="seq-stage">
        <canvas ref={canvasRef} className="seq-canvas" aria-hidden="true" />
        <div className="seq-veil" aria-hidden="true" />
        <p ref={loaderRef} className="seq-loader" aria-live="polite" />
        {captions.map((caption, k) => (
          <div
            key={caption.kicker}
            ref={(el) => {
              captionRefs.current[k] = el;
            }}
            className="seq-caption"
          >
            <p className="seq-kicker">{caption.kicker}</p>
            <h2>{caption.title}</h2>
            <p className="seq-body">{caption.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
