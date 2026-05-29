const readline = require('readline');
const { stdout, stdin } = process;

// ── State ──────────────────────────────────────────────
let mode = 'focus';          // focus | shortBreak | longBreak
let timerState = 'idle';     // idle | running | paused
let timeLeft = 25 * 60;      // seconds
let totalTime = 25 * 60;
let completedSessions = 0;
let interval = null;
let settings = { focus: 25 * 60, shortBreak: 5 * 60, longBreak: 15 * 60 };

const LABEL = { focus: 'FOCUS', shortBreak: 'BREAK', longBreak: 'REST' };
const RING_COLOR = { focus: 255, shortBreak: 109, longBreak: 111 }; // 256-color indices

// ── Terminal setup ─────────────────────────────────────
stdout.write('\x1b[?25l'); // hide cursor
stdin.setRawMode(true);
stdin.resume();
stdin.setEncoding('utf8');

function clear() { stdout.write('\x1b[2J\x1b[H'); }
function moveTo(row, col) { stdout.write(`\x1b[${row};${col}H`); }
function color(n) { return `\x1b[38;5;${n}m`; }
function reset() { return '\x1b[0m'; }
function bold() { return '\x1b[1m'; }
function dim() { return '\x1b[2m'; }

function getSize() {
  return { w: stdout.columns || 80, h: stdout.rows || 24 };
}

// ── Draw ───────────────────────────────────────────────
function draw() {
  const { w, h } = getSize();
  const cx = Math.floor(w / 2);
  const cy = Math.floor(h / 2);
  const radius = Math.min(14, Math.floor(h / 2) - 6);

  clear();

  // Mode tabs
  const modes = ['focus', 'shortBreak', 'longBreak'];
  const tabLabels = ['Focus', 'Break', 'Rest'];
  const tabStr = modes.map((m, i) => {
    const s = ` ${tabLabels[i]} `;
    if (m === mode) return `${bold()}${color(RING_COLOR[mode])}[${s}]${reset()}`;
    return `${dim()}[${s}]${reset()}`;
  }).join('  ');
  moveTo(cy - radius - 3, cx - Math.floor(tabStr.replace(/\x1b\[[0-9;]*m/g, '').length / 2));
  stdout.write(tabStr);

  // ASCII ring
  const progress = 1 - timeLeft / totalTime;
  const chars = '▁▂▃▄▅▆▇█';
  for (let row = -radius; row <= radius; row++) {
    moveTo(cy + row, 1);
    for (let col = 0; col < w; col++) {
      const dx = col - cx;
      const dy = row;
      const dist = Math.sqrt(dx * dx + dy * dy);
      // Ring boundaries
      const inner = radius - 1.2;
      const outer = radius + 0.5;
      if (dist >= inner && dist <= outer) {
        // Calculate angle (0 at top, going clockwise)
        const angle = (Math.atan2(dy, dx) + Math.PI / 2 + Math.PI * 2) % (Math.PI * 2);
        const filled = angle / (Math.PI * 2) <= progress;
        const ch = pickChar(dist, inner, outer);
        if (filled) {
          stdout.write(`${bold()}${color(RING_COLOR[mode])}${ch}${reset()}`);
        } else {
          stdout.write(`${color(237)}${ch}${reset()}`);
        }
      } else {
        stdout.write(' ');
      }
    }
  }

  // Time display
  const mm = Math.floor(timeLeft / 60);
  const ss = timeLeft % 60;
  const timeStr = `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
  moveTo(cy - 1, cx - Math.floor(timeStr.length / 2));
  stdout.write(`${bold()}${timeStr}${reset()}`);
  moveTo(cy + 1, cx - Math.floor(LABEL[mode].length / 2));
  stdout.write(`${dim()}${LABEL[mode]}${reset()}`);

  // Controls
  const btnLabel = timerState === 'running' ? 'Pause' : timerState === 'paused' ? 'Resume' : 'Start';
  const ctrlStr = `[Space] ${btnLabel}  [R] Reset  [S] Skip  [1/2/3] Mode  [Q] Quit`;
  moveTo(cy + radius + 2, cx - Math.floor(ctrlStr.length / 2));
  stdout.write(dim() + ctrlStr + reset());

  // Session dots
  const dots = Array.from({ length: 4 }, (_, i) => i < completedSessions ? `${color(RING_COLOR[mode])}●${reset()}` : `${dim()}○${reset()}`).join(' ');
  moveTo(cy + radius + 4, cx - Math.floor(4 * 2 - 1));
  stdout.write(dots);

  // Running indicator
  if (timerState === 'running') {
    moveTo(cy - radius - 1, cx);
    const pulse = Math.floor(Date.now() / 600) % 3;
    stdout.write(pulse === 0 ? ' ' : pulse === 1 ? '·' : ' ');
  }
}

function pickChar(dist, inner, outer) {
  const t = (dist - inner) / (outer - inner); // 0..1
  if (t < 0.2) return ' ';
  if (t < 0.4) return '░';
  if (t < 0.6) return '▒';
  if (t < 0.8) return '▓';
  return '█';
}

// ── Timer logic ────────────────────────────────────────
function tick() {
  if (timerState !== 'running') return;
  timeLeft--;
  draw();
  if (timeLeft <= 0) finish();
}

function startTimer() {
  if (timerState === 'running') return;
  timerState = 'running';
  interval = setInterval(tick, 1000);
  draw();
}

function pauseTimer() {
  timerState = 'paused';
  clearInterval(interval);
  interval = null;
  draw();
}

function resetTimer() {
  clearInterval(interval);
  interval = null;
  timerState = 'idle';
  timeLeft = settings[mode === 'shortBreak' ? 'shortBreak' : mode === 'longBreak' ? 'longBreak' : 'focus'];
  totalTime = timeLeft;
  draw();
}

function skipTimer() {
  finish();
}

function setMode(m) {
  clearInterval(interval);
  interval = null;
  timerState = 'idle';
  mode = m;
  timeLeft = settings[mode === 'shortBreak' ? 'shortBreak' : mode === 'longBreak' ? 'longBreak' : 'focus'];
  totalTime = timeLeft;
  draw();
}

function finish() {
  clearInterval(interval);
  interval = null;
  beep();

  if (mode === 'focus') {
    completedSessions++;
    if (completedSessions >= 4) {
      completedSessions = 0;
      setMode('longBreak');
    } else {
      setMode('shortBreak');
    }
  } else {
    setMode('focus');
  }
  startTimer();
}

function beep() {
  stdout.write('\x07'); // terminal bell
}

// ── Settings ───────────────────────────────────────────
function showSettings() {
  clear();
  const { w, h } = getSize();
  const cx = Math.floor(w / 2);
  const cy = Math.floor(h / 2);

  const lines = [
    '',
    `${bold()}Settings${reset()}`,
    '',
    `Focus: ${settings.focus / 60} min  [f/F]`,
    `Break: ${settings.shortBreak / 60} min  [b/B]`,
    `Rest:  ${settings.longBreak / 60} min  [l/L]`,
    '',
    `${dim()}↑↓ 1min  ⇧↑↓ 5min  [Enter] back${reset()}`,
  ];

  lines.forEach((line, i) => {
    moveTo(cy - 4 + i, cx - Math.floor(30 / 2));
    stdout.write(line);
  });
}

// ── Input ──────────────────────────────────────────────
let settingsMode = false;
let settingsKey = null;

stdin.on('data', (key) => {
  if (settingsMode) {
    handleSettingsInput(key);
    return;
  }

  switch (key) {
    case ' ':
      if (timerState === 'running') pauseTimer();
      else startTimer();
      break;
    case 'r': case 'R':
      resetTimer();
      break;
    case 's': case 'S':
      skipTimer();
      break;
    case '1': setMode('focus'); break;
    case '2': setMode('shortBreak'); break;
    case '3': setMode('longBreak'); break;
    case ',': case '<':
      settingsMode = true;
      showSettings();
      break;
    case 'q': case 'Q':
    case '\x03': // Ctrl+C
      cleanup();
      process.exit(0);
  }
});

function handleSettingsInput(key) {
  const delta = (s, dir) => Math.max(1, Math.min(s + dir * 60, 120 * 60));
  const big = key === key.toUpperCase() ? 5 : 1;

  if (key === '\r' || key === '\n' || key === ',' || key === '<') {
    settingsMode = false;
    resetTimer();
    return;
  }

  switch (key) {
    case 'f': settings.focus = delta(settings.focus, -big); break;
    case 'F': settings.focus = delta(settings.focus, big); break;
    case 'b': settings.shortBreak = delta(settings.shortBreak, -big); break;
    case 'B': settings.shortBreak = delta(settings.shortBreak, big); break;
    case 'l': settings.longBreak = delta(settings.longBreak, -big); break;
    case 'L': settings.longBreak = delta(settings.longBreak, big); break;
    case '\x03': cleanup(); process.exit(0);
  }
  showSettings();
}

// ── Cleanup ────────────────────────────────────────────
function cleanup() {
  clearInterval(interval);
  stdout.write('\x1b[?25h'); // show cursor
  stdin.setRawMode(false);
  stdin.pause();
  clear();
}

process.on('exit', cleanup);
process.on('SIGINT', () => { cleanup(); process.exit(0); });

// Handle terminal resize
stdout.on('resize', draw);

// ── Start ──────────────────────────────────────────────
draw();
