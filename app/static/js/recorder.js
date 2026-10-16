/*
 * oyuKids recorder — see the `recorder` macro in templates/partials/_ui.html.
 * Records the mic, POSTs `audio` + `duration_ms` (+ hidden inputs) to data-upload-url,
 * then swaps the returned HTML into data-target via htmx.
 */
(function () {
  "use strict";

  const MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  const BAR_COLORS = ["#FF6B6B", "#FFC83D", "#2ED3A0", "#4CC9F0", "#8B5CF6"];

  const pickMimeType = () =>
    (window.MediaRecorder && MIME_TYPES.find((m) => MediaRecorder.isTypeSupported(m))) || "";

  const extFor = (mime) => (mime.includes("wav") ? ".wav" : mime.includes("mp4") ? ".m4a" : mime.includes("ogg") ? ".ogg" : ".webm");

  // Recordings are stored as training data, so they go up as 16 kHz mono 16-bit PCM WAV —
  // the usual speech-corpus format, and accepted by the STT. Decoding/resampling uses Web Audio.
  const WAV_RATE = 16000;

  async function toWav(blob) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    let decoded;
    try {
      decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
    } finally {
      ctx.close();
    }
    const offline = new OfflineAudioContext(1, Math.max(1, Math.ceil(decoded.duration * WAV_RATE)), WAV_RATE);
    const source = offline.createBufferSource();
    source.buffer = decoded;
    source.connect(offline.destination); // mono destination → channels are down-mixed
    source.start();
    return encodeWav((await offline.startRendering()).getChannelData(0), WAV_RATE);
  }

  function encodeWav(samples, rate) {
    const view = new DataView(new ArrayBuffer(44 + samples.length * 2));
    const text = (offset, str) => [...str].forEach((ch, i) => view.setUint8(offset + i, ch.charCodeAt(0)));
    text(0, "RIFF"); view.setUint32(4, 36 + samples.length * 2, true); text(8, "WAVE");
    text(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    text(36, "data"); view.setUint32(40, samples.length * 2, true);
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return new Blob([view], { type: "audio/wav" });
  }

  const formatMs = (ms) => {
    const s = Math.floor(ms / 1000);
    return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  };

  function init(root) {
    if (root.dataset.ready) return;
    root.dataset.ready = "1";

    const button = root.querySelector("[data-rec-btn]");
    const timer = root.querySelector("[data-rec-timer]");
    const status = root.querySelector("[data-rec-status]");
    const demo = root.querySelector("[data-rec-demo]");
    const canvas = root.querySelector("canvas");
    const maxMs = (Number(root.dataset.maxSeconds) || 180) * 1000;

    let recorder = null;
    let stream = null;
    let audioCtx = null;
    let startedAt = 0;
    let tickId = null;
    let frameId = null;
    let chunks = [];

    const setStatus = (text) => status && (status.textContent = text);
    const setBusy = (busy) => {
      root.classList.toggle("is-busy", busy);
      button.disabled = busy;
      if (demo) demo.disabled = busy;
    };

    async function start() {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        setStatus("Энэ хөтөч бичлэг хийх боломжгүй байна. Доорх туршилтын товчийг ашиглаарай.");
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      } catch {
        setStatus("Микрофон ашиглах зөвшөөрөл өгөөрэй 🎤");
        return;
      }
      const mimeType = pickMimeType();
      recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunks = [];
      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      recorder.onstop = () => upload(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }), Date.now() - startedAt);
      recorder.start(250);

      startedAt = Date.now();
      root.classList.add("is-recording");
      setStatus("Бичиж байна… Дуусмагц товчийг дахин дараарай");
      tickId = setInterval(() => {
        const elapsed = Date.now() - startedAt;
        timer.textContent = formatMs(elapsed);
        if (elapsed >= maxMs) stop();
      }, 200);
      visualize();
    }

    function stop() {
      clearInterval(tickId);
      cancelAnimationFrame(frameId);
      root.classList.remove("is-recording");
      if (recorder && recorder.state !== "inactive") recorder.stop();
      stream?.getTracks().forEach((t) => t.stop());
      audioCtx?.close();
      audioCtx = null;
      drawBars(null);
    }

    // levels: 24 values in 0..1, or null for the resting (idle) state
    function drawBars(levels) {
      if (!canvas) return;
      const g = canvas.getContext("2d");
      const bars = 24;
      const slot = canvas.width / bars;
      g.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < bars; i++) {
        const h = levels ? Math.max(6, levels[i] * canvas.height) : 6 + 8 * Math.abs(Math.sin(i * 0.7));
        const x = i * slot + slot * 0.2;
        const y = (canvas.height - h) / 2;
        g.fillStyle = levels ? BAR_COLORS[i % BAR_COLORS.length] : "#EFE7DA";
        g.beginPath();
        g.roundRect ? g.roundRect(x, y, slot * 0.6, h, 4) : g.rect(x, y, slot * 0.6, h);
        g.fill();
      }
    }

    function visualize() {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!canvas || !Ctx) return;
      audioCtx = new Ctx();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      audioCtx.createMediaStreamSource(stream).connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const draw = () => {
        analyser.getByteFrequencyData(data);
        drawBars(Array.from(data, (v) => v / 255));
        frameId = requestAnimationFrame(draw);
      };
      draw();
    }

    async function upload(blob, durationMs) {
      setBusy(true);
      setStatus("Оюу шалгаж байна… 🦉");
      if (blob.size) {
        try {
          blob = await toWav(blob);
        } catch (err) {
          console.warn("WAV conversion failed; sending the original recording", err);
        }
      }
      const body = new FormData();
      body.append("audio", blob, "recording" + extFor(blob.type));
      body.append("duration_ms", String(Math.round(durationMs)));
      root.querySelectorAll("input[type=hidden]").forEach((input) => body.append(input.name, input.value));

      try {
        const res = await fetch(root.dataset.uploadUrl, { method: "POST", body, headers: { "HX-Request": "true" } });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        swap(await res.text());
      } catch (err) {
        console.error(err);
        setBusy(false);
        setStatus("Уучлаарай, алдаа гарлаа. Дахин оролдоно уу.");
      }
    }

    function swap(html) {
      const target = document.querySelector(root.dataset.target) || root;
      if (window.htmx?.swap) {
        htmx.swap(target, html, { swapStyle: "innerHTML" });
      } else {
        target.innerHTML = html;
        window.htmx?.process(target);
      }
      initAll(target);
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    drawBars(null);
    button.addEventListener("click", () => (root.classList.contains("is-recording") ? stop() : start()));

    // No-mic demo: posts an empty clip with a plausible duration; the mock STT fakes the transcript.
    demo?.addEventListener("click", () => {
      const seconds = (Number(root.dataset.demoSeconds) || 15) * (0.8 + Math.random() * 0.5);
      upload(new Blob([], { type: "audio/webm" }), seconds * 1000);
    });
  }

  function initAll(scope) {
    const el = scope || document;
    if (el.matches?.("[data-recorder]")) init(el);
    el.querySelectorAll?.("[data-recorder]").forEach(init);
  }

  document.addEventListener("DOMContentLoaded", () => initAll());
  if (window.htmx) htmx.onLoad(initAll);
})();
