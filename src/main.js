import { gsap } from "gsap";

const actors = [
  { name: "suit", frameCount: 14, framesPerSecond: 3 },
  { name: "floral", frameCount: 46, framesPerSecond: 5 },
  { name: "seated", frameCount: 20, framesPerSecond: 3 },
  { name: "cyclist", frameCount: 20, framesPerSecond: 6 },
  { name: "dancer", frameCount: 20, framesPerSecond: 8 },
];

const spriteLoops = [];

for (const config of actors) {
  const actor = document.querySelector(`[data-actor="${config.name}"]`);
  if (!actor) continue;

  const strip = actor.querySelector("img");
  if (!strip) continue;

  actor.style.setProperty("--sprite-strip-width", `${config.frameCount * 100}%`);

  gsap.set(strip, {
    xPercent: 0,
    force3D: true,
  });

  spriteLoops.push({
    frameCount: config.frameCount,
    framesPerSecond: config.framesPerSecond,
    setFrame: gsap.quickSetter(strip, "xPercent"),
    lastFrame: -1,
    offset: Number(actor.dataset.offset || 0),
  });
}

gsap.ticker.lagSmoothing(500, 16);

gsap.ticker.add((time) => {
  for (const loop of spriteLoops) {
    const frame = Math.floor((time + loop.offset) * loop.framesPerSecond) % loop.frameCount;
    if (frame === loop.lastFrame) continue;

    loop.setFrame(-(frame * 100) / loop.frameCount);
    loop.lastFrame = frame;
  }
});

const cyclist = document.querySelector('[data-actor="cyclist"]');

if (cyclist) {
  gsap.set(cyclist, {
    left: "-18%",
    top: "104%",
    x: 0,
    y: 0,
    rotation: 0,
  });

  gsap.to(cyclist, {
    left: "125%",
    top: "-26%",
    duration: 16,
    ease: "none",
    repeat: -1,
  });
}
