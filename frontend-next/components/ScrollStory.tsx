"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

gsap.registerPlugin(ScrollTrigger);

const FRAMES_PER_CHAPTER = 120;
const TOTAL_FRAMES = FRAMES_PER_CHAPTER * 4;

const CHAPTERS = [
  {
    folder: "/scroll/ch1",
    kicker: "01 / 04",
    title: "Read the documents first.",
    body: "Every draft starts from the shipment's own invoice, bill of lading, packing list and certificate of origin.",
  },
  {
    folder: "/scroll/ch2",
    kicker: "02 / 04",
    title: "Every charge is checked against the tariff card.",
    body: "Handling, documentation and storage lines are compared with the rate for the container size on the card.",
  },
  {
    folder: "/scroll/ch3",
    kicker: "03 / 04",
    title: "Storage days are recounted from the gate dates.",
    body: "Dwell time runs from gate in to gate out, less the free days on the card. Each flag names the tariff line it was measured against.",
  },
  {
    folder: "/scroll/ch4",
    kicker: "04 / 04",
    title: "You approve before anything is copied.",
    body: "Unsupported sentences are rejected and listed. Nothing is sent from this page.",
  },
] as const;

const FADE = 0.06;

function frameSrc(index: number) {
  const chapter = CHAPTERS[Math.floor(index / FRAMES_PER_CHAPTER)];
  const local = (index % FRAMES_PER_CHAPTER) + 1;
  return `${chapter.folder}/frame_${String(local).padStart(4, "0")}.webp`;
}

export default function ScrollStory() {
  const trackRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const captionRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const track = trackRef.current;
    const stage = stageRef.current;
    const canvas = canvasRef.current;
    if (!track || !stage || !canvas) return;

    const ctx2d = canvas.getContext("2d");
    if (!ctx2d) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) track.classList.add("is-static");
    const images: HTMLImageElement[] = [];
    let current = -1;

    for (let i = 0; i < TOTAL_FRAMES; i++) {
      const img = new Image();
      img.decoding = "async";
      img.onload = () => {
        if (i === current) drawFrame(i);
      };
      img.src = frameSrc(i);
      images.push(img);
    }

    function drawFrame(index: number) {
      if (!ctx2d || !canvas) return;
      const img = images[index];
      if (!img || !img.complete || !img.naturalWidth) return;
      const cw = canvas.width;
      const ch = canvas.height;
      const scale = Math.max(cw / img.naturalWidth, ch / img.naturalHeight);
      const dw = img.naturalWidth * scale;
      const dh = img.naturalHeight * scale;
      ctx2d.clearRect(0, 0, cw, ch);
      ctx2d.drawImage(img, (cw - dw) / 2, (ch - dh) / 2, dw, dh);
      current = index;
    }

    function resize() {
      if (!canvas) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const height = reduceMotion ? window.innerHeight * 0.6 : window.innerHeight;
      canvas.width = Math.round(window.innerWidth * dpr);
      canvas.height = Math.round(height * dpr);
      drawFrame(Math.max(current, 0));
    }

    resize();
    window.addEventListener("resize", resize);

    const captions = captionRefs.current.filter(
      (el): el is HTMLDivElement => el !== null,
    );

    if (reduceMotion) {
      drawFrame(Math.floor(TOTAL_FRAMES / 2));
      return () => window.removeEventListener("resize", resize);
    }

    const lenis = new Lenis({ duration: 1.2, smoothWheel: true });
    lenis.on("scroll", ScrollTrigger.update);
    const tick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);

    const ctx = gsap.context(() => {
      // Caption milestones: 0-25%, 25-50%, 50-75%, 75-100%.
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: track,
          start: "top top",
          end: "bottom bottom",
          scrub: true,
          onUpdate: (self) => {
            const index = Math.min(TOTAL_FRAMES - 1, Math.round(self.progress * (TOTAL_FRAMES - 1)));
            if (index !== current) drawFrame(index);
          },
        },
      });

      captions.forEach((el, k) => {
        const start = k * 0.25;
        const end = start + 0.25;
        if (k === 0) {
          gsap.set(el, { autoAlpha: 1, y: 0 });
        } else {
          tl.fromTo(
            el,
            { autoAlpha: 0, y: 28 },
            { autoAlpha: 1, y: 0, duration: FADE, ease: "power2.out" },
            start,
          );
        }
        if (k < captions.length - 1) {
          tl.to(el, { autoAlpha: 0, y: -18, duration: FADE, ease: "power2.in" }, end - FADE);
        }
      });
      tl.set({}, {}, 1);

      ScrollTrigger.create({
        trigger: track,
        start: "top top",
        end: "bottom bottom",
        pin: stage,
        pinSpacing: false,
      });
    }, track);

    return () => {
      ctx.revert();
      gsap.ticker.remove(tick);
      lenis.destroy();
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <section ref={trackRef} className="story-track" aria-label="How a shipment is checked">
      <div ref={stageRef} className="story-stage">
        <canvas ref={canvasRef} className="story-canvas" aria-hidden="true" />
        <div className="story-veil" aria-hidden="true" />
        {CHAPTERS.map((chapter, k) => (
          <div
            key={chapter.kicker}
            ref={(el) => {
              captionRefs.current[k] = el;
            }}
            className="story-caption"
          >
            <p className="story-kicker">{chapter.kicker}</p>
            <h2>{chapter.title}</h2>
            <p className="story-body">{chapter.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
