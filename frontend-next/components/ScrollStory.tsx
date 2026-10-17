"use client";

import FrameSequence from "@/components/FrameSequence";

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

function chapterFrameUrl(index: number) {
  const chapter = CHAPTERS[Math.floor(index / FRAMES_PER_CHAPTER)];
  const local = (index % FRAMES_PER_CHAPTER) + 1;
  return `${chapter.folder}/frame_${String(local).padStart(4, "0")}.webp`;
}

export default function ScrollStory() {
  return (
    <FrameSequence
      frameUrl={chapterFrameUrl}
      count={TOTAL_FRAMES}
      captions={CHAPTERS}
      ariaLabel="How a shipment is checked"
    />
  );
}
