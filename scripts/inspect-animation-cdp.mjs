const port = process.env.CDP_PORT || "9235";
const targetUrl = process.env.TARGET_URL || "http://127.0.0.1:5174/";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function openTab() {
  let response = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(targetUrl)}`, {
    method: "PUT",
  });

  if (!response.ok) {
    response = await fetch(`http://127.0.0.1:${port}/json/list`);
    const pages = await response.json();
    return pages.find((page) => page.type === "page");
  }

  return response.json();
}

async function send(ws, method, params = {}) {
  const id = send.nextId++;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`CDP timeout: ${method}`)), 10000);
    send.pending.set(id, (message) => {
      clearTimeout(timeout);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
    });
  });
}
send.nextId = 1;
send.pending = new Map();

const page = await openTab();
if (!page?.webSocketDebuggerUrl) {
  throw new Error("Could not find a debuggable Chrome page");
}

const ws = new WebSocket(page.webSocketDebuggerUrl);
ws.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  const resolver = send.pending.get(message.id);
  if (resolver) {
    send.pending.delete(message.id);
    resolver(message);
  }
});

await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));
await send(ws, "Runtime.enable");
await sleep(500);

const expression = `new Promise((resolve) => {
  const actor = document.querySelector('[data-actor="suit"]');
  const strip = actor?.querySelector('img');
  const samples = [];
  let last = performance.now();
  let ticks = 0;

  function sample(now) {
    const style = getComputedStyle(strip);
    const actorRect = actor.getBoundingClientRect();
    samples.push({
      at: now,
      delta: now - last,
      transform: style.transform,
      animationDuration: style.animationDuration,
      animationTimingFunction: style.animationTimingFunction,
      naturalWidth: strip.naturalWidth,
      naturalHeight: strip.naturalHeight,
      clientWidth: strip.clientWidth,
      actorWidth: actor.clientWidth,
      actorLeft: actorRect.left,
      actorTop: actorRect.top,
      actorRight: actorRect.right,
      actorBottom: actorRect.bottom,
    });
    last = now;
    ticks += 1;
    if (ticks < 360) requestAnimationFrame(sample);
    else resolve(samples);
  }

  requestAnimationFrame(sample);
})`;

const result = await send(ws, "Runtime.evaluate", {
  expression,
  awaitPromise: true,
  returnByValue: true,
});

const samples = result.result.value;
const transforms = samples.map((sample) => sample.transform);
const changes = [];
for (let index = 1; index < transforms.length; index += 1) {
  if (transforms[index] !== transforms[index - 1]) {
    changes.push(samples[index].at - samples[index - 1].at);
  }
}

const uniqueTransforms = [...new Set(transforms)];
const deltas = samples.map((sample) => sample.delta).slice(1);
const summary = {
  sampleCount: samples.length,
  uniqueTransformCount: uniqueTransforms.length,
  firstFrame: {
    naturalWidth: samples[0].naturalWidth,
    naturalHeight: samples[0].naturalHeight,
    clientWidth: samples[0].clientWidth,
    actorWidth: samples[0].actorWidth,
    animationDuration: samples[0].animationDuration,
    animationTimingFunction: samples[0].animationTimingFunction,
  },
  maxRafDelta: Math.max(...deltas),
  averageRafDelta: deltas.reduce((sum, delta) => sum + delta, 0) / deltas.length,
  transformChangeCount: changes.length,
  actorRectRange: {
    left: [Math.min(...samples.map((sample) => sample.actorLeft)), Math.max(...samples.map((sample) => sample.actorLeft))],
    top: [Math.min(...samples.map((sample) => sample.actorTop)), Math.max(...samples.map((sample) => sample.actorTop))],
    right: [Math.min(...samples.map((sample) => sample.actorRight)), Math.max(...samples.map((sample) => sample.actorRight))],
    bottom: [Math.min(...samples.map((sample) => sample.actorBottom)), Math.max(...samples.map((sample) => sample.actorBottom))],
  },
};

console.log(JSON.stringify(summary, null, 2));
ws.close();
