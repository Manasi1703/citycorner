const actors = [
  { name: "suit", frameCount: 14, framesPerSecond: 3 },
  { name: "floral", frameCount: 46, framesPerSecond: 5 },
  { name: "seated", frameCount: 20, framesPerSecond: 3 },
  { name: "dancer", frameCount: 20, framesPerSecond: 8 },
];

for (const config of actors) {
  const actor = document.querySelector(`[data-actor="${config.name}"]`);
  if (!actor) continue;

  actor.style.setProperty("--sprite-strip-width", `${config.frameCount * 100}%`);
  actor.style.setProperty("--sprite-loop-duration", `${config.frameCount / config.framesPerSecond}s`);
  actor.style.setProperty("--sprite-timing", `steps(${config.frameCount})`);
}
