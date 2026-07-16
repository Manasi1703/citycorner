import { gsap } from "gsap";

const actors = [
  { name: "suit", frameCount: 14, framesPerSecond: 3 },
  { name: "floral", frameCount: 46, framesPerSecond: 5 },
  { name: "seated", frameCount: 20, framesPerSecond: 3 },
  { name: "cyclist", frameCount: 20, framesPerSecond: 6 },
  { name: "dancer", frameCount: 20, framesPerSecond: 8 },
];

for (const config of actors) {
  const actor = document.querySelector(`[data-actor="${config.name}"]`);
  if (!actor) continue;

  actor.style.setProperty("--sprite-strip-width", `${config.frameCount * 100}%`);
  actor.style.setProperty("--sprite-loop-duration", `${config.frameCount / config.framesPerSecond}s`);
  actor.style.setProperty("--sprite-timing", `steps(${config.frameCount})`);
}

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
