import FrameSequence from "@/components/FrameSequence";

const SEQUENCE_CAPTIONS = [
  {
    kicker: "Sequence",
    title: "Cargo moves along the route.",
    body: "Scroll to play the sequence forward, and scroll back to run it in reverse.",
  },
];

export default function SequencePage() {
  return (
    <main>
      <FrameSequence
        framePattern="/sequence/frame_{n3}.webp"
        count={120}
        captions={SEQUENCE_CAPTIONS}
        ariaLabel="Cargo vehicle moving along the route"
        pinVh={400}
      />
    </main>
  );
}
