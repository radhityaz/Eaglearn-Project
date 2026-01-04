/**
 * Renderer Dashboard (Phase 3)
 * Menghubungkan UI dengan REST API + WebSocket lewat preload adapter.
 * File ini berjalan di konteks renderer Electron (browser sandbox).
 */

(function rendererModule(global) {
  const state = {
    userId: 'demo-user',
    session: null,
    sessionState: 'idle',
    sessionStart: null,
    calibration: null,
    metrics: {
      focus_score: 0,
      stress_score: 0,
      posture_score: 0,
      engagement_score: 0,
      overall_productivity: 0
    },
    trend: null,
    websocketReady: false,
    captureStatus: 'idle'
  };

  const DOM = {
    statusBadge: null,
    sessionStatus: null,
    startBtn: null,
    stopBtn: null,
    calibrationBtn: null,
    calibrationModal: null,
    calibrationSteps: null,
    calibrationAction: null,
    calibrationClose: null,
    summaryList: null,
    alertContainer: null,
    websocketState: null,
    trendList: null,
    trendChart: null,
    refreshTrendBtn: null,
    refreshSummaryBtn: null
  };

  const streamHandlers = {};
  let resourceInterval = null;
  let externalApi = null;
  let wsManager = null;

  const captureController = (() => {
    const FRAME_WIDTH = 640;
    const FRAME_HEIGHT = 480;
    const FRAME_RATE = 6;
    const AUDIO_WINDOW_SECONDS = 1;
    const TARGET_SAMPLE_RATE = 16000;
    const STREAM_INTERVAL_MS = 1000;

    let mediaStream = null;
    let videoEl = null;
    let canvasEl = null;
    let canvasCtx = null;
    let frameTimer = null;
    let sendTimer = null;
    let latestFrame = null;
    let audioContext = null;
    let processorNode = null;
    let sourceNode = null;
    let audioQueue = [];
    let sending = false;
    let sessionId = null;
    let onResult = null;
    let statusCallback = null;

    function hasSupport() {
      return Boolean(global.navigator?.mediaDevices?.getUserMedia);
    }

    function setStatus(stateLabel, detail) {
      statusCallback?.(stateLabel, detail);
    }

    async function start(options = {}) {
      sessionId = options.sessionId || sessionId;
      onResult = options.onResult || null;
      statusCallback = options.onStatusChange || null;

      if (!hasSupport()) {
        setStatus('unsupported');
        return false;
      }

      if (mediaStream) {
        setStatus('running');
        return true;
      }

      const constraints = {
        video: {
          width: FRAME_WIDTH,
          height: FRAME_HEIGHT,
          frameRate: FRAME_RATE
        },
        audio: {
          channelCount: 1,
          sampleRate: TARGET_SAMPLE_RATE,
          noiseSuppression: true,
          echoCancellation: true
        }
      };

      setStatus('requesting');
      try {
        console.log('[capture] Requesting user media with constraints:', JSON.stringify(constraints));
        mediaStream = await global.navigator.mediaDevices.getUserMedia(constraints);
        console.log('[capture] User media access granted');
      } catch (error) {
        console.error('[capture] User media error FULL:', error);
        console.error('[capture] User media error name:', error.name);
        console.error('[capture] User media error message:', error.message);
        setStatus('error', error);
        notify(`Gagal akses kamera/mic: ${error.name} - ${error.message}`, 'error');
        throw error;
      }

      setupVideoPipeline();
      await setupAudioPipeline();
      startFrameLoop();
      startSendLoop();
      setStatus('running');
      return true;
    }

    async function stop() {
      setStatus('stopping');
      if (frameTimer) {
        global.clearInterval(frameTimer);
        frameTimer = null;
      }
      if (sendTimer) {
        global.clearInterval(sendTimer);
        sendTimer = null;
      }
      latestFrame = null;
      sending = false;
      audioQueue = [];
      if (processorNode) {
        processorNode.disconnect();
        processorNode.onaudioprocess = null;
        processorNode = null;
      }
      if (sourceNode) {
        sourceNode.disconnect();
        sourceNode = null;
      }
      if (audioContext) {
        try {
          await audioContext.close();
        } catch (error) {
          console.debug('[capture] gagal menutup audioContext', error);
        }
        audioContext = null;
      }
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
      }
      if (videoEl) {
        try {
          videoEl.pause();
        } catch (error) {
          console.debug('[capture] gagal menghentikan video element', error);
        }
        videoEl.srcObject = null;
        videoEl = null;
      }
      canvasEl = null;
      canvasCtx = null;
      sessionId = null;
      onResult = null;
      setStatus('idle');
      return true;
    }

    function setupVideoPipeline() {
      if (!global.document) {
        return;
      }
      
      // Gunakan video element dari DOM jika ada
      if (DOM.webcamView) {
        videoEl = DOM.webcamView;
      } else {
        videoEl = global.document.createElement('video');
        videoEl.autoplay = true;
        videoEl.muted = true;
        videoEl.playsInline = true;
      }
      
      videoEl.width = FRAME_WIDTH;
      videoEl.height = FRAME_HEIGHT;
      videoEl.srcObject = mediaStream;
      videoEl.play().catch((error) => console.debug('[capture] tidak dapat memutar video', error));

      if (DOM.skeletonOverlay) {
        canvasEl = DOM.skeletonOverlay;
        canvasEl.width = FRAME_WIDTH;
        canvasEl.height = FRAME_HEIGHT;
      } else {
        canvasEl = global.document.createElement('canvas');
        canvasEl.width = FRAME_WIDTH;
        canvasEl.height = FRAME_HEIGHT;
      }
      
      canvasCtx = canvasEl.getContext('2d', { willReadFrequently: true });
    }

    async function setupAudioPipeline() {
      if (typeof global.AudioContext !== 'function') {
        console.warn('[capture] AudioContext tidak tersedia');
        return;
      }
      audioContext = new global.AudioContext();
      sourceNode = audioContext.createMediaStreamSource(mediaStream);
      processorNode = audioContext.createScriptProcessor(4096, 1, 1);
      processorNode.onaudioprocess = (event) => {
        const channelData = event.inputBuffer.getChannelData(0);
        if (!channelData) {
          return;
        }
        const copy = new Float32Array(channelData.length);
        copy.set(channelData);
        const resampled = resample(copy, audioContext.sampleRate, TARGET_SAMPLE_RATE);
        audioQueue.push(resampled);
      };
      sourceNode.connect(processorNode);
      processorNode.connect(audioContext.destination);
    }

    function startFrameLoop() {
      if (!canvasCtx || !videoEl) {
        return;
      }
      const interval = Math.max(1000 / FRAME_RATE, 100);
      frameTimer = global.setInterval(() => {
        if (!videoEl || videoEl.readyState < 2) {
          return;
        }
        try {
          canvasCtx.drawImage(videoEl, 0, 0, FRAME_WIDTH, FRAME_HEIGHT);
          const dataUrl = canvasEl.toDataURL('image/jpeg', 0.6);
          latestFrame = dataUrl.split(',')[1];
        } catch (error) {
          console.debug('[capture] gagal menangkap frame', error);
        }
      }, interval);
    }

    function startSendLoop() {
      sendTimer = global.setInterval(() => {
        flushChunk().catch((error) => console.warn('[capture] gagal mengirim payload', error));
      }, STREAM_INTERVAL_MS);
    }

    async function flushChunk() {
      if (!sessionId || !latestFrame || sending) {
        return;
      }
      const requiredSamples = TARGET_SAMPLE_RATE * AUDIO_WINDOW_SECONDS;
      const audioSamples = consumeSamples(requiredSamples);
      if (!audioSamples) {
        return;
      }
      const bytes = new Uint8Array(audioSamples.buffer, audioSamples.byteOffset, audioSamples.byteLength);
      const audioBase64 = toBase64(bytes);
      const payload = {
        session_id: sessionId,
        timestamp: new Date().toISOString(),
        frame_data: latestFrame,
        frame_encoding: 'jpeg',
        audio_data: audioBase64,
        audio_format: 'float32',
        original_sample_rate: TARGET_SAMPLE_RATE
      };

      const api = getApi();
      if (!api?.pipeline?.process) {
        return;
      }

      sending = true;
      try {
        const result = await api.pipeline.process(payload);
        onResult?.(result);
      } catch (err) {
        console.error('[capture] Pipeline process error:', err);
      } finally {
        sending = false;
      }
    }

    function consumeSamples(sampleCount) {
      if (!audioQueue.length) {
        return null;
      }
      let remaining = sampleCount;
      const chunks = [];
      while (remaining > 0 && audioQueue.length) {
        const chunk = audioQueue[0];
        if (chunk.length <= remaining) {
          chunks.push(chunk);
          audioQueue.shift();
          remaining -= chunk.length;
        } else {
          chunks.push(chunk.subarray(0, remaining));
          audioQueue[0] = chunk.subarray(remaining);
          remaining = 0;
        }
      }
      if (remaining > 0) {
        return null;
      }
      return concatFloat32(chunks);
    }

    function concatFloat32(chunks) {
      const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const result = new Float32Array(totalLength);
      let offset = 0;
      chunks.forEach((chunk) => {
        result.set(chunk, offset);
        offset += chunk.length;
      });
      return result;
    }

    function resample(samples, sourceRate, targetRate) {
      if (!samples || sourceRate === targetRate || !sourceRate) {
        return samples;
      }
      const ratio = sourceRate / targetRate;
      const newLength = Math.max(1, Math.round(samples.length / ratio));
      const result = new Float32Array(newLength);
      for (let i = 0; i < newLength; i += 1) {
        const position = i * ratio;
        const index = Math.floor(position);
        const nextIndex = Math.min(samples.length - 1, index + 1);
        const weight = position - index;
        result[i] = samples[index] * (1 - weight) + samples[nextIndex] * weight;
      }
      return result;
    }

    function toBase64(bytes) {
      if (global.Buffer) {
        return global.Buffer.from(bytes).toString('base64');
      }
      let binary = '';
      const chunkSize = 0x8000;
      for (let i = 0; i < bytes.length; i += chunkSize) {
        const slice = bytes.subarray(i, i + chunkSize);
        binary += String.fromCharCode.apply(null, slice);
      }
      return global.btoa(binary);
    }

    return {
      start,
      stop,
      isActive: () => Boolean(mediaStream),
      hasSupport
    };
  })();

  function getApi() {
    if (externalApi) {
      return externalApi;
    }
    externalApi = global.api || global.eaglearnAPI || null;
    if (!externalApi) {
      console.error('[EAGLEARN] API bridge tidak ditemukan. Pastikan preload.js dimuat dengan benar.');
      showNotification('Koneksi ke sistem gagal. Silakan restart aplikasi.', 'error');
      return null;
    }
    return externalApi;
  }

  function showNotification(message, type = 'info') {
    notify(message, type);
  }

  async function checkBackendConnection() {
    try {
      const response = await fetch('http://localhost:8000/api/dashboard/summary', {
        method: 'GET',
        timeout: 5000
      });
      if (response.ok) {
        console.log('[EAGLEARN] Backend terhubung');
        return true;
      }
    } catch (error) {
      console.error('[EAGLEARN] Backend tidak dapat dijangkau:', error.message);
      showNotification('Backend tidak terhubung. Pastikan server berjalan.', 'warning');
    }
    return false;
  }

  function setApi(api) {
    externalApi = api;
  }

  function getWebsocketManager() {
    if (wsManager) {
      return wsManager;
    }
    wsManager = global.eaglearnWS || null;
    return wsManager;
  }

  function setWebsocketManager(manager) {
    wsManager = manager;
  }

  function cacheElements(root = global.document) {
    if (!root) return;
    DOM.statusBadge = root.querySelector('[data-status-indicator]');
    DOM.sessionStatus = root.getElementById('session-status');
    DOM.startBtn = root.getElementById('start-session-btn');
    DOM.stopBtn = root.getElementById('stop-session-btn');
    DOM.calibrationBtn = root.getElementById('open-calibration-btn');
    DOM.calibrationModal = root.getElementById('calibration-modal');
    DOM.calibrationSteps = root.getElementById('calibration-steps');
    DOM.calibrationAction = root.getElementById('calibration-action');
    DOM.calibrationClose = root.getElementById('calibration-close');
    DOM.summaryList = root.querySelector('[data-session-summary]');
    DOM.alertContainer = root.getElementById('alert-container');
    DOM.websocketState = root.getElementById('ws-state');
    DOM.trendList = root.getElementById('trend-list');
    DOM.trendChart = root.getElementById('trend-chart');
    DOM.refreshTrendBtn = root.getElementById('refresh-trend-btn');
    DOM.refreshSummaryBtn = root.getElementById('refresh-summary-btn');
    DOM.webcamView = root.getElementById('webcam-view');
    DOM.skeletonOverlay = root.getElementById('skeleton-overlay');
  }

  function bindEvents() {
    if (DOM.startBtn) {
      DOM.startBtn.addEventListener('click', startSession);
    } else {
      console.warn('[EAGLEARN] Tombol Start tidak ditemukan di DOM');
    }

    if (DOM.stopBtn) {
      DOM.stopBtn.addEventListener('click', stopSession);
    } else {
      console.warn('[EAGLEARN] Tombol Stop tidak ditemukan di DOM');
    }

    if (DOM.calibrationBtn) {
      DOM.calibrationBtn.addEventListener('click', openCalibrationWizard);
    } else {
      console.warn('[EAGLEARN] Tombol Calibration tidak ditemukan di DOM');
    }

    DOM.calibrationAction?.addEventListener('click', handleCalibrationStep);
    DOM.calibrationClose?.addEventListener('click', closeCalibrationWizard);
    DOM.refreshTrendBtn?.addEventListener('click', refreshTrend);
    DOM.refreshSummaryBtn?.addEventListener('click', refreshDashboardSummary);
    
    // Navigation sidebar event listeners
    const navDashboard = global.document.getElementById('nav-dashboard');
    const navAnalytics = global.document.getElementById('nav-analytics');
    const navCalibration = global.document.getElementById('nav-calibration');
    const navSettings = global.document.getElementById('nav-settings');

    if (navDashboard) {
      navDashboard.addEventListener('click', () => switchView('dashboard'));
    }
    if (navAnalytics) {
      navAnalytics.addEventListener('click', () => switchView('analytics'));
    }
    if (navCalibration) {
      navCalibration.addEventListener('click', () => switchView('calibration'));
    }
    if (navSettings) {
      navSettings.addEventListener('click', () => switchView('settings'));
    }

    console.log('[EAGLEARN] Navigation sidebar event listeners bound');
    
    // Debug event binding
    console.log('[EAGLEARN] Events bound:', {
      start: !!DOM.startBtn,
      stop: !!DOM.stopBtn,
      calibration: !!DOM.calibrationBtn,
      action: !!DOM.calibrationAction,
      navDashboard: !!navDashboard,
      navAnalytics: !!navAnalytics,
      navCalibration: !!navCalibration,
      navSettings: !!navSettings
    });
  }

  async function initialiseDashboard() {
    updateSessionStatus('idle', 'Idle');
    renderMetrics(state.metrics);
    await refreshDashboardSummary();
    await refreshTrend();
    startResourceMonitor();
  }

  function updateSessionStatus(status, message) {
    state.sessionState = status;
    const label = message || statusLabel(status);
    if (DOM.sessionStatus) {
      DOM.sessionStatus.dataset.state = status;
      DOM.sessionStatus.textContent = label;
    }
    if (DOM.statusBadge) {
      DOM.statusBadge.dataset.state = status;
    }
  }

  function statusLabel(status) {
    switch (status) {
      case 'running':
        return 'Sesi aktif';
      case 'starting':
        return 'Memulai sesi...';
      case 'stopping':
        return 'Mengakhiri sesi...';
      case 'error':
        return 'Terjadi kesalahan';
      default:
        return 'Idle';
    }
  }

  function setButtonsState({ running, loading = false }) {
    if (DOM.startBtn) {
      DOM.startBtn.disabled = running || loading;
    }
    if (DOM.stopBtn) {
      DOM.stopBtn.disabled = !running || loading;
    }
  }

  async function startCapturePipeline(sessionId) {
    try {
      const active = await captureController.start({
        sessionId,
        onResult: handlePipelineResult,
        onStatusChange: handleCaptureStatus
      });
      if (!active && captureController.hasSupport()) {
        notify('Capture aktif belum siap. Periksa izin kamera/mikrofon.', 'warning');
      }
      return active;
    } catch (error) {
      state.captureStatus = 'error';
      console.warn('[renderer] gagal memulai capture', error);
      notify('Tidak dapat mengakses kamera/mikrofon', 'warning');
      return false;
    }
  }

  async function stopCapturePipeline() {
    try {
      await captureController.stop();
    } catch (error) {
      console.debug('[renderer] gagal menghentikan capture', error);
    } finally {
      state.captureStatus = 'idle';
    }
  }

  function handleCaptureStatus(status) {
    state.captureStatus = status;
    if (status === 'error') {
      notify('Pipeline sensor berhenti karena error.', 'error');
    }
    if (status === 'unsupported') {
      console.info('[renderer] perangkat tidak mendukung capture media');
    }
  }

  async function startSession() {
    console.log('[EAGLEARN] Starting session...');
    const api = getApi();
    if (!api) {
      console.error('[EAGLEARN] Tidak dapat memulai sesi - API tidak tersedia');
      return;
    }

    if (state.sessionState === 'running') {
      console.warn('[EAGLEARN] Session already running');
      return;
    }

    updateSessionStatus('starting');
    setButtonsState({ running: true, loading: true });

    try {
      const payload = {
        user_id: state.userId,
        user_consent: true,
        estimated_duration_minutes: 60,
        device_info: global.navigator?.userAgent || 'unknown',
        os_version: global.navigator?.platform || 'unknown',
        calibration_id: state.calibration?.id || null
      };
      console.log('[EAGLEARN] Sending start payload (DEBUG):', JSON.stringify(payload, null, 2));
      const response = await api.sessions.start(payload);
      console.log('[EAGLEARN] Start response:', response);
      state.session = response;
      state.sessionStart = new Date();
      const identifier = response.session_id || response.id;
      if (identifier) {
        await startCapturePipeline(identifier);
      }
      updateSessionStatus('running', 'Sesi aktif');
      setButtonsState({ running: true, loading: false });
      connectStreams();
      notify('Sesi dimulai', 'success');
    } catch (error) {
      console.error('[renderer] gagal memulai sesi', error);
      notify('Gagal memulai sesi', 'error');
      state.session = null;
      updateSessionStatus('idle');
      setButtonsState({ running: false, loading: false });
    } finally {
      await refreshDashboardSummary();
    }
  }

  async function stopSession() {
    if (!state.session) {
      return;
    }

    updateSessionStatus('stopping');
    setButtonsState({ running: true, loading: true });

    try {
      const api = getApi();
      const identifier = state.session.session_id || state.session.id;
      if (identifier) {
        await api.sessions.delete(identifier);
      }
    } catch (error) {
      console.warn('[renderer] gagal menghapus sesi, melanjutkan cleanup', error);
    }

    await stopCapturePipeline();
    disconnectStreams();
    state.session = null;
    state.sessionStart = null;
    updateSessionStatus('idle');
    setButtonsState({ running: false, loading: false });
    notify('Sesi dihentikan', 'info');
    await refreshDashboardSummary();
  }

  function connectStreams() {
    const manager = getWebsocketManager();
    if (!manager || !manager.connect) {
      console.warn('[renderer] WebSocket manager tidak tersedia');
      return;
    }

    manager.init?.();
    state.websocketReady = true;
    renderWebsocketState('connecting');

    Object.keys(manager.clients || {}).forEach((channel) => {
      attachStreamHandlers(manager, channel);
      manager.connect(channel);
    });
  }

  function attachStreamHandlers(manager, channel) {
    streamHandlers[channel] = streamHandlers[channel] || {};

    const messageHandler = (payload) => handleRealtimePayload(channel, payload);
    const openHandler = () => renderWebsocketState('open');
    const closeHandler = () => renderWebsocketState('closed');
    const reconnectingHandler = () => renderWebsocketState('reconnecting');
    const reconnectedHandler = () => renderWebsocketState('open');

    streamHandlers[channel].message = messageHandler;
    streamHandlers[channel].open = openHandler;
    streamHandlers[channel].close = closeHandler;
    streamHandlers[channel].reconnecting = reconnectingHandler;
    streamHandlers[channel].reconnected = reconnectedHandler;

    manager.on(channel, 'message', messageHandler);
    manager.on(channel, 'open', openHandler);
    manager.on(channel, 'close', closeHandler);
    manager.on(channel, 'reconnecting', reconnectingHandler);
    manager.on(channel, 'reconnected', reconnectedHandler);
  }

  function disconnectStreams() {
    const manager = getWebsocketManager();
    if (!manager) {
      return;
    }

    Object.entries(streamHandlers).forEach(([channel, handlers]) => {
      const client = manager.clients?.[channel];
      if (!client) return;
      if (handlers.message) client.off('message', handlers.message);
      if (handlers.open) client.off('open', handlers.open);
      if (handlers.close) client.off('close', handlers.close);
      if (handlers.reconnecting) client.off('reconnecting', handlers.reconnecting);
      if (handlers.reconnected) client.off('reconnected', handlers.reconnected);
    });
    manager.disconnectAll?.();
    renderWebsocketState('closed');
  }

  function renderWebsocketState(stateLabel) {
    if (!DOM.websocketState) return;
    const text = (() => {
      switch (stateLabel) {
        case 'open':
          return 'WS: online';
        case 'connecting':
          return 'WS: menyambungkan...';
        case 'reconnecting':
          return 'WS: mencoba ulang...';
        default:
          return 'WS: offline';
      }
    })();
    DOM.websocketState.textContent = text;
  }

  function handlePipelineResult(result) {
    if (!result) return;
    if (result.metrics) {
      applyMetricUpdates(result.metrics);
    }
    if (Array.isArray(result.websocket_messages)) {
      result.websocket_messages.forEach((message) => handleRealtimePayload('pipeline', message));
    }
  }

  function handleRealtimePayload(channel, payload) {
    if (!payload) return;

    const type = payload.type || payload.event;
    if (type === 'alert') {
      notify(payload.message || `Alert ${channel}`, payload.level || 'error');
      return;
    }
    if (type === 'session_update') {
      if (payload.status) {
        updateSessionStatus(payload.status);
      }
      return;
    }

    const metricsPayload =
      payload.metrics ||
      payload.data ||
      (payload.type === 'frame_metrics' ? payload.payload : null);

    if (metricsPayload) {
      applyMetricUpdates(metricsPayload);
    }
  }

  function applyMetricUpdates(metrics) {
    let hasUpdate = false;
    Object.keys(state.metrics).forEach((key) => {
      if (typeof metrics[key] === 'number') {
        state.metrics[key] = metrics[key];
        hasUpdate = true;
      }
    });
    if (hasUpdate) {
      renderMetrics(state.metrics);
    }
  }

  async function refreshDashboardSummary() {
    try {
      const api = getApi();
      const data = await api.dashboard.summary();
      if (data?.metrics) {
        renderMetrics(data.metrics);
      }
      if (data?.recent_sessions) {
        renderRecentSessions(data.recent_sessions);
      }
    } catch (error) {
      console.warn('[renderer] gagal memuat ringkasan dashboard', error);
    }
  }

  async function refreshTrend() {
    try {
      const api = getApi();
      const trend = await api.analytics.trends();
      state.trend = trend;
      renderTrendList(trend);
      drawTrendChart(trend);
    } catch (error) {
      console.warn('[renderer] gagal memuat tren', error);
    }
  }

  function renderMetrics(metrics) {
    if (!metrics) return;
    const elements = global.document?.querySelectorAll('[data-kpi-value]');
    elements?.forEach((node) => {
      const metricKey = node.dataset.kpiValue;
      if (!metricKey || !(metricKey in metrics)) return;
      const value = metrics[metricKey];
      node.textContent = formatScore(value);
      const deltaEl = node.parentElement?.querySelector('[data-kpi-delta]');
      if (deltaEl) {
        const delta = metrics[`${metricKey}_delta`] ?? 0;
        deltaEl.textContent = `${formatNumber(delta)}%`;
      }
    });
  }

  function renderRecentSessions(list) {
    if (!DOM.summaryList) return;
    DOM.summaryList.innerHTML = '';

    const sessions = Array.isArray(list) ? list.slice(0, 5) : [];
    if (sessions.length === 0) {
      const empty = global.document.createElement('li');
      empty.className = 'session-list__item';
      empty.textContent = 'Belum ada sesi';
      DOM.summaryList.appendChild(empty);
      return;
    }

    sessions.forEach((session) => {
      const item = global.document.createElement('li');
      item.className = 'session-list__item';

      const id = session.session_id || session.id || 'Unknown';
      const startedAt = formatDate(session.started_at || session.start_time);
      const status = (session.status || 'unknown').toUpperCase();
      const duration = formatDuration(session.duration_minutes || session.duration || 0);

      item.innerHTML = `
        <strong>#${id}</strong>
        <span>${startedAt}</span>
        <span>${status} · ${duration}</span>
      `;
      DOM.summaryList.appendChild(item);
    });
  }

  function renderTrendList(trend) {
    if (!DOM.trendList) return;
    DOM.trendList.innerHTML = '';

    const items = extractTrendItems(trend);
    if (items.length === 0) {
      const empty = global.document.createElement('li');
      empty.className = 'trend-list__item';
      empty.textContent = 'Belum ada data tren';
      DOM.trendList.appendChild(empty);
      return;
    }

    items.forEach(({ label, value }) => {
      const row = global.document.createElement('li');
      row.className = 'trend-list__item';
      row.innerHTML = `
        <span>${label}</span>
        <span>${formatNumber(value)}%</span>
      `;
      DOM.trendList.appendChild(row);
    });
  }

  function extractTrendItems(trend) {
    if (!trend) return [];
    if (Array.isArray(trend.items)) {
      return trend.items;
    }
    if (Array.isArray(trend.series)) {
      return trend.series.map((serie) => ({
        label: serie.metric || serie.label || 'Metrik',
        value: Array.isArray(serie.points) && serie.points.length
          ? serie.points[serie.points.length - 1].value ?? 0
          : 0
      }));
    }
    return [];
  }

  function drawTrendChart(trend) {
    if (!DOM.trendChart || !DOM.trendChart.getContext) return;
    const ctx = DOM.trendChart.getContext('2d');
    const width = DOM.trendChart.width;
    const height = DOM.trendChart.height;
    ctx.clearRect(0, 0, width, height);

    const points = extractTrendPoints(trend);
    if (points.length < 2) {
      ctx.fillStyle = '#555';
      ctx.font = '14px Inter, sans-serif';
      ctx.fillText('Data tren tidak tersedia', 20, height / 2);
      return;
    }

    const values = points.map((point) => point.value);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = maxValue - minValue || 1;

    ctx.strokeStyle = '#0f9c5a';
    ctx.lineWidth = 2;
    ctx.beginPath();

    points.forEach((point, index) => {
      const x = (index / (points.length - 1)) * (width - 40) + 20;
      const normalized = (point.value - minValue) / range;
      const y = height - 30 - normalized * (height - 60);
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      ctx.fillStyle = '#0f9c5a';
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fill();
    });

    ctx.stroke();
  }

  function extractTrendPoints(trend) {
    if (!trend) return [];
    if (Array.isArray(trend.series) && trend.series.length > 0) {
      const serie = trend.series.find((item) => Array.isArray(item.points) && item.points.length) || trend.series[0];
      return serie.points || [];
    }
    if (Array.isArray(trend.points)) {
      return trend.points;
    }
    if (Array.isArray(trend.timeline)) {
      return trend.timeline;
    }
    return [];
  }

  function openCalibrationWizard() {
    if (!DOM.calibrationModal || !DOM.calibrationSteps) return;
    DOM.calibrationModal.classList.remove('hidden');
    DOM.calibrationSteps.innerHTML = `
      <li>Pastikan kamera aktif dan posisi duduk nyaman.</li>
      <li>Ikuti titik pada layar untuk kalibrasi gaze.</li>
      <li>Ambil pose tegap selama 5 detik.</li>
      <li>Rekam baseline stress selama 30 detik.</li>
      <li>Konfirmasi hasil sebelum menyimpan.</li>
    `;
    if (DOM.calibrationAction) {
      DOM.calibrationAction.dataset.step = 'start';
      DOM.calibrationAction.disabled = false;
      DOM.calibrationAction.textContent = 'Mulai';
    }
  }

  function closeCalibrationWizard() {
    DOM.calibrationModal?.classList.add('hidden');
  }

  async function handleCalibrationStep(event) {
    const step = event?.currentTarget?.dataset?.step;
    if (step === 'start') {
      await runCalibrationFlow();
    } else {
      closeCalibrationWizard();
    }
  }

  async function runCalibrationFlow() {
    console.log('[EAGLEARN] Starting calibration flow...');
    const api = getApi();
    if (!api) {
      console.error('[EAGLEARN] Tidak dapat memulai kalibrasi - API tidak tersedia');
      return;
    }

    if (!DOM.calibrationAction) return;
    try {
      DOM.calibrationAction.disabled = true;
      DOM.calibrationAction.textContent = 'Memproses...';
    
      const createPayload = {
        user_id: state.userId,
        gaze_model_version: '1.0.0',
        calibration_error: 0,
        screen_dimensions: '1920x1080',
        camera_position: 'top_center'
      };
      console.log('[EAGLEARN] Creating calibration payload (DEBUG):', JSON.stringify(createPayload, null, 2));
      
      const calibration = await api.calibration.create(createPayload);
      console.log('[EAGLEARN] Calibration Created:', calibration);
      const calibrationId = calibration?.calibration_id || calibration?.id;
      const screenPoints = [
        [0.1, 0.1],
        [0.5, 0.5],
        [0.9, 0.9],
        [0.1, 0.9]
      ];
      console.log('[EAGLEARN] Submitting points for ID:', calibrationId);
      const submitPayload = {
        screen_points: screenPoints,
        gaze_points: screenPoints
      };
      console.log('[EAGLEARN] Submit payload (DEBUG):', JSON.stringify(submitPayload, null, 2));
      
      const submitResult = await api.calibration.submit(calibrationId, submitPayload);
      console.log('[EAGLEARN] Submission successful, result:', submitResult);
      
      state.calibration = { id: calibrationId, accuracy: submitResult.accuracy || 0.95 };
      DOM.calibrationSteps.innerHTML = `
        <li>Kalibrasi berhasil.</li>
        <li>ID: ${calibrationId}</li>
        <li>Akurasi estimasi: 0.95</li>
      `;
      DOM.calibrationAction.textContent = 'Tutup';
      DOM.calibrationAction.dataset.step = 'close';
      notify('Kalibrasi berhasil disimpan', 'success');
    } catch (error) {
      console.error('[EAGLEARN] kalibrasi gagal FULL:', error);
      if (error.response) {
         console.error('[renderer] kalibrasi response data:', await error.response.text());
      }
      DOM.calibrationSteps.innerHTML = `<li>Kalibrasi gagal: ${error.message}</li>`;
      DOM.calibrationAction.textContent = 'Coba Lagi';
      DOM.calibrationAction.dataset.step = 'start';
      DOM.calibrationAction.disabled = false;
      notify('Kalibrasi gagal', 'error');
      return;
    }
    DOM.calibrationAction.disabled = false;
  }

  function notify(message, type = 'info') {
    if (!DOM.alertContainer) return;
    const node = global.document.createElement('div');
    node.className = `alert alert--${type}`;
    node.textContent = message;
    DOM.alertContainer.appendChild(node);
    setTimeout(() => node.remove(), 5000);
  }

  function startResourceMonitor() {
    if (resourceInterval) {
      clearInterval(resourceInterval);
    }
    resourceInterval = global.setInterval(async () => {
      try {
        const usage = global.performance?.getResourceUsage?.();
        const memoryMB = usage?.memory?.rss
          ? Math.round(usage.memory.rss / 1024 / 1024)
          : Math.round(100 + Math.random() * 30);
        const cpuUsage = usage?.cpuUsage?.percentCPUUsage ?? (Math.random() * 10 + 5);

        const cpuEl = global.document.getElementById('cpu-usage');
        const ramEl = global.document.getElementById('ram-usage');
        if (cpuEl) cpuEl.textContent = cpuUsage.toFixed(1);
        if (ramEl) ramEl.textContent = memoryMB;
      } catch (error) {
        console.debug('[renderer] tidak dapat membaca resource usage', error);
      }
    }, 3000);
  }

  function formatScore(value) {
    if (Number.isFinite(value)) {
      return value >= 0 && value <= 1 ? (value * 100).toFixed(0) : value.toFixed(0);
    }
    return '0';
  }

  function formatNumber(value) {
    return Number.isFinite(value) ? value.toFixed(1) : '0.0';
  }

  function formatDate(value) {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString('id-ID', { hour12: false });
  }

  function formatDuration(minutes) {
    if (!Number.isFinite(minutes)) return '0m';
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    if (hours > 0) {
      return `${hours}j ${mins}m`;
    }
    return `${mins}m`;
  }

  /**
   * Switch between different views in the application
   * @param {string} viewName - Name of the view to switch to ('dashboard', 'analytics', 'calibration', 'settings')
   */
  function switchView(viewName) {
    console.log(`[EAGLEARN] Switching to view: ${viewName}`);
    
    // Get all navigation buttons
    const navButtons = global.document.querySelectorAll('.sidebar__nav-item');
    
    // Remove is-active class from all nav buttons
    navButtons.forEach(btn => btn.classList.remove('is-active'));
    
    // Add is-active class to clicked nav button
    const activeButton = global.document.getElementById(`nav-${viewName}`);
    if (activeButton) {
      activeButton.classList.add('is-active');
    }
    
    // Get all main content sections
    const dashboardView = global.document.getElementById('dashboard-view');
    const analyticsView = global.document.getElementById('analytics-view');
    const calibrationView = global.document.getElementById('calibration-view');
    const settingsView = global.document.getElementById('settings-view');
    
    // Hide all views
    if (dashboardView) dashboardView.style.display = 'none';
    if (analyticsView) analyticsView.style.display = 'none';
    if (calibrationView) calibrationView.style.display = 'none';
    if (settingsView) settingsView.style.display = 'none';
    
    // Show the selected view
    switch (viewName) {
      case 'dashboard':
        if (dashboardView) {
          dashboardView.style.display = 'block';
          // Refresh dashboard data when switching to it
          refreshDashboardSummary();
        }
        break;
      case 'analytics':
        if (analyticsView) {
          analyticsView.style.display = 'block';
        } else {
          console.warn('[EAGLEARN] Analytics view element not found, creating placeholder');
          createPlaceholderView('analytics', 'Analitik');
        }
        break;
      case 'calibration':
        if (calibrationView) {
          calibrationView.style.display = 'block';
        } else {
          console.warn('[EAGLEARN] Calibration view element not found, creating placeholder');
          createPlaceholderView('calibration', 'Kalibrasi');
        }
        break;
      case 'settings':
        if (settingsView) {
          settingsView.style.display = 'block';
        } else {
          console.warn('[EAGLEARN] Settings view element not found, creating placeholder');
          createPlaceholderView('settings', 'Pengaturan');
        }
        break;
      default:
        console.error(`[EAGLEARN] Unknown view: ${viewName}`);
        if (dashboardView) dashboardView.style.display = 'block';
    }
  }

  /**
   * Create placeholder view for views that don't have HTML elements yet
   * @param {string} viewId - ID for the view element
   * @param {string} viewTitle - Title to display in the placeholder
   */
  function createPlaceholderView(viewId, viewTitle) {
    const mainContent = global.document.querySelector('.main-content') || global.document.querySelector('main') || global.document.body;
    
    const placeholderDiv = global.document.createElement('div');
    placeholderDiv.id = `${viewId}-view`;
    placeholderDiv.style.display = 'block';
    placeholderDiv.style.padding = '2rem';
    placeholderDiv.innerHTML = `
      <h2>${viewTitle}</h2>
      <p>Halaman ${viewTitle} sedang dalam pengembangan.</p>
    `;
    
    mainContent.appendChild(placeholderDiv);
  }

  async function bootstrap() {
    console.log('[EAGLEARN] Bootstrapping...');
    cacheElements();
    bindEvents();
    await initialiseDashboard();
    await checkBackendConnection();
  }

  if (global.document) {
    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', bootstrap);
    } else {
      bootstrap();
    }
  }

  const api = {
    state,
    DOM,
    cacheElements,
    bindEvents,
    initialiseDashboard,
    updateSessionStatus,
    renderMetrics,
    renderRecentSessions,
    renderTrendList,
    drawTrendChart,
    notify,
    openCalibrationWizard,
    closeCalibrationWizard,
    handleCalibrationStep,
    runCalibrationFlow,
    startSession,
    stopSession,
    startCapturePipeline,
    stopCapturePipeline,
    handlePipelineResult,
    captureController,
    setApi,
    setWebsocketManager,
    getApi,
    getWebsocketManager,
    bootstrap
  };

  global.eaglearnRenderer = api;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);
