# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A Pomodoro timer with two standalone implementations — no build step, no dependencies.

## Running

```
# Browser version (SVG ring, notifications, sound)
start pomodoro.html

# Terminal version (ASCII ring, keyboard controls)
node pomodoro.js
```

Terminal controls: `Space` start/pause, `R` reset, `S` skip, `1/2/3` switch mode, `,` settings, `Q` quit.

## Architecture

Both files are self-contained: inline CSS + vanilla JS in HTML, single Node.js script with no imports. They share the same state machine (idle → running → paused, focus → shortBreak → longBreak) but don't share code. Each is complete and modifies independently.
