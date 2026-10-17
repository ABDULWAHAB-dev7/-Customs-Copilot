export type PreloadOptions = {
  concurrency?: number;
  onFrame: (index: number, image: HTMLImageElement) => void;
  onError?: (index: number, url: string) => void;
  isCancelled?: () => boolean;
};

function decodeImage(url: string): Promise<HTMLImageElement> {
  const image = new Image();
  image.decoding = "async";
  image.src = url;
  return image.decode().then(() => image);
}

export async function preloadSequence(urls: string[], options: PreloadOptions): Promise<void> {
  const concurrency = options.concurrency ?? 6;
  let next = 0;

  async function worker() {
    while (next < urls.length) {
      if (options.isCancelled?.()) return;
      const index = next++;
      try {
        const image = await decodeImage(urls[index]);
        if (options.isCancelled?.()) return;
        options.onFrame(index, image);
      } catch {
        options.onError?.(index, urls[index]);
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(concurrency, urls.length) }, worker));
}
