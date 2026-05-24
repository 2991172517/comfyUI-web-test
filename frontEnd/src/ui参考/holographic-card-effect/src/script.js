const card = document.querySelector(".card");
const rotator = document.querySelector(".card__rotator");

// State
const rotationSpring = createSpring({ x: 0, y: 0 });
const backgroundSpring = createSpring({ x: 50, y: 50 });
const pointerSpring = createSpring({ x: 50, y: 50, effectIntensity: 0 });
const springs = [rotationSpring, backgroundSpring, pointerSpring];

let frameId = null;
let lastTimestamp = 0;
let resetTimer = null;
let springSettings;

// Configuration
const springInteractSettings = {
  stiffness: 0.066,
  damping: 0.25
};

const springReturnSettings = {
  stiffness: 0.01,
  damping: 0.06
};

// Main flow
springSettings = springInteractSettings;

if (card && rotator) {
  card.addEventListener("pointermove", handlePointerMove);
  card.addEventListener("pointerleave", handlePointerLeave);
  card.addEventListener("pointercancel", handlePointerLeave);
}

// Visual updates
function setRotation({ x, y }) {
  rotator.style.setProperty("--tilt-left-right", `${x}deg`);
  rotator.style.setProperty("--tilt-up-down", `${y}deg`);
}

function setShineBackground({ x, y }) {
  rotator.style.setProperty("--background-x", `${x}%`);
  rotator.style.setProperty("--background-y", `${y}%`);
}

function getPointerDistanceFromCenter(x, y) {
  const distance = Math.hypot(x - 50, y - 50) / 50;

  return round(clamp(distance, 0, 1));
}

function setPointer({ x, y, effectIntensity }) {
  rotator.style.setProperty("--pointer-x", `${x}%`);
  rotator.style.setProperty("--pointer-y", `${y}%`);
  rotator.style.setProperty(
    "--pointer-from-center",
    getPointerDistanceFromCenter(x, y)
  );
  rotator.style.setProperty("--effect-intensity", effectIntensity);
}

function applyVisualState() {
  setRotation({
    x: round(rotationSpring.current.x),
    y: round(rotationSpring.current.y)
  });

  setShineBackground({
    x: round(backgroundSpring.current.x),
    y: round(backgroundSpring.current.y)
  });
  setPointer({
    x: round(pointerSpring.current.x),
    y: round(pointerSpring.current.y),
    effectIntensity: round(pointerSpring.current.effectIntensity)
  });
}

// Animation loop
function animateCard(timestamp) {
  if (!lastTimestamp) {
    lastTimestamp = timestamp;
  }

  const deltaTime = Math.min((timestamp - lastTimestamp) / 16.666, 4);
  lastTimestamp = timestamp;

  springs.forEach((spring) => {
    updateSpring(spring, deltaTime);
  });

  if (springs.every(isCloseToTarget)) {
    springs.forEach(finishSpringAtTarget);
    applyVisualState();
    frameId = null;
    lastTimestamp = 0;
    return;
  }

  applyVisualState();

  frameId = requestAnimationFrame(animateCard);
}

function startAnimation() {
  if (frameId === null) {
    frameId = requestAnimationFrame(animateCard);
  }
}

// Pointer interaction
function handlePointerMove(event) {
  clearTimeout(resetTimer);
  resetTimer = null;
  springSettings = springInteractSettings;

  const rect = card.getBoundingClientRect();
  const pointerPosition = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  };

  const pointer = {
    x: round(clamp((pointerPosition.x / rect.width) * 100)),
    y: round(clamp((pointerPosition.y / rect.height) * 100))
  };

  const center = {
    x: pointer.x - 50,
    y: pointer.y - 50
  };

  setSpringTarget(rotationSpring, {
    // Same tilt strength: 50% center offset becomes about 14deg.
    x: round(-(center.x / 3.5)),
    y: round(center.y / 3.5)
  });
  setSpringTarget(backgroundSpring, {
    x: mapRange(pointer.x, 0, 100, 37, 63),
    y: mapRange(pointer.y, 0, 100, 33, 67)
  });
  setSpringTarget(pointerSpring, {
    x: pointer.x,
    y: pointer.y,
    effectIntensity: 1
  });

  startAnimation();
}

function handlePointerLeave(event, delay = 500) {
  clearTimeout(resetTimer);

  resetTimer = setTimeout(() => {
    springSettings = springReturnSettings;
    setSpringTarget(rotationSpring, { x: 0, y: 0 });
    setSpringTarget(backgroundSpring, { x: 50, y: 50 });
    setSpringTarget(pointerSpring, { x: 50, y: 50, effectIntensity: 0 });
    resetTimer = null;
    startAnimation();
  }, delay);
}

// Utility functions
function mapRange(value, fromMin, fromMax, toMin, toMax) {
  const progress = (value - fromMin) / (fromMax - fromMin);

  return round(toMin + progress * (toMax - toMin));
}

function clamp(value, min = 0, max = 100) {
  return Math.min(Math.max(value, min), max);
}

function round(value, precision = 3) {
  return Number(value.toFixed(precision));
}

// Custom spring implementation
function createSpring(initialValue) {
  const axes = Object.keys(initialValue);

  return {
    axes,
    current: { ...initialValue },
    target: { ...initialValue },
    velocity: Object.fromEntries(axes.map((axis) => [axis, 0]))
  };
}

function setSpringTarget(spring, value) {
  Object.assign(spring.target, value);
}

function resetSpringVelocity(spring) {
  spring.axes.forEach((axis) => {
    spring.velocity[axis] = 0;
  });
}

function updateSpring(spring, deltaTime) {
  spring.axes.forEach((axis) => {
    const distance = spring.target[axis] - spring.current[axis];

    spring.velocity[axis] += distance * springSettings.stiffness * deltaTime;
    spring.velocity[axis] *= Math.pow(1 - springSettings.damping, deltaTime);
    spring.current[axis] += spring.velocity[axis] * deltaTime;
  });
}

const STOP_THRESHOLD = 0.001;
function isCloseToTarget(spring) {
  return spring.axes.every((axis) => {
    const distance = Math.abs(spring.target[axis] - spring.current[axis]);
    const speed = Math.abs(spring.velocity[axis]);

    return distance < STOP_THRESHOLD && speed < STOP_THRESHOLD;
  });
}

function finishSpringAtTarget(spring) {
  spring.current = { ...spring.target };
  resetSpringVelocity(spring);
}
