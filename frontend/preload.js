const { contextBridge, ipcRenderer } = require('electron');

const DEFAULT_API_BASE = process.env.BACKEND_API_BASE || 'http://localhost:8000/api';
const DEFAULT_WS_BASE = process.env.BACKEND_WS_BASE || 'ws://localhost:8000';

function deriveCoreBase(apiBase) {
  const trimmed = (apiBase || '').replace(/\/$/, '');
  if (trimmed.endsWith('/api')) {
    return trimmed.slice(0, -4) || trimmed;
  }
  return trimmed || apiBase;
}

const state = {
  apiBase: DEFAULT_API_BASE.replace(/\/$/, ''),
  wsBase: DEFAULT_WS_BASE.replace(/\/$/, ''),
  coreBase: (process.env.BACKEND_CORE_BASE || deriveCoreBase(DEFAULT_API_BASE)).replace(/\/$/, '')
};

function buildUrl(base, path, query) {
  const normalizedBase = (base || '').replace(/\/$/, '');
  const normalizedPath = path.startsWith('/') ? path.slice(1) : path;
  const url = new URL(`${normalizedBase}/${normalizedPath}`);
  if (query) {
    Object.entries(query)
      .filter(([, value]) => value !== undefined && value !== null)
      .forEach(([key, value]) => url.searchParams.append(key, String(value)));
  }
  return url;
}

async function requestTo(base, method, path, { body, query, headers } = {}) {
  const url = buildUrl(base, path, query);
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(headers || {})
    }
  };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  const text = await response.text();
  if (!response.ok) {
    const detail = text || response.statusText;
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`Failed to parse JSON response from ${url.pathname}: ${error.message}`);
  }
}

function request(method, path, options) {
  return requestTo(state.apiBase, method, path, options);
}

function requestCore(method, path, options) {
  return requestTo(state.coreBase || state.apiBase, method, path, options);
}

const apiAdapter = {
  config: {
    get baseUrl() {
      return state.apiBase;
    },
    set baseUrl(url) {
      state.apiBase = url.replace(/\/$/, '');
      state.coreBase = deriveCoreBase(state.apiBase);
    },
    get wsBaseUrl() {
      return state.wsBase;
    },
    set wsBaseUrl(url) {
      state.wsBase = url.replace(/\/$/, '');
    },
    get coreBaseUrl() {
      return state.coreBase;
    },
    set coreBaseUrl(url) {
      state.coreBase = (url || '').replace(/\/$/, '');
    }
  },
  system: {
    getInfo: () => ipcRenderer.invoke('get-system-info'),
    versions: {
      node: process.versions.node,
      chrome: process.versions.chrome,
      electron: process.versions.electron
    }
  },
  sessions: {
    start(payload) {
      return request('POST', '/sessions', { body: payload });
    },
    get(sessionId, options = {}) {
      return request('GET', `/sessions/${sessionId}`, {
        query: options.includeMetrics ? { include_metrics: true } : undefined
      });
    },
    list(params = {}) {
      return request('GET', '/sessions', { query: params });
    },
    delete(sessionId) {
      return request('DELETE', `/sessions/${sessionId}`);
    }
  },
  calibration: {
    create(payload) {
      return request('POST', '/calibration', { body: payload });
    },
    get(userId) {
      return request('GET', `/calibration/${userId}`);
    },
    submit(calibrationId, payload) {
      return request('POST', `/calibration/${calibrationId}/submit`, { body: payload });
    }
  },
  metrics: {
    gaze(payload) {
      return request('POST', '/metrics/gaze', { body: payload });
    },
    pose(payload) {
      return request('POST', '/metrics/pose', { body: payload });
    },
    stress(payload) {
      return request('POST', '/metrics/stress', { body: payload });
    },
    productivity(payload) {
      return request('POST', '/metrics/productivity', { body: payload });
    }
  },
  dashboard: {
    summary() {
      return request('GET', '/dashboard/summary');
    }
  },
  analytics: {
    trends() {
      return request('GET', '/analytics/trends');
    }
  },
  pipeline: {
    process(payload) {
      return requestCore('POST', '/v1/pipeline/process', { body: payload });
    }
  }
};

contextBridge.exposeInMainWorld('api', apiAdapter);

// Backwards compatibility for legacy renderer references
contextBridge.exposeInMainWorld('eaglearnAPI', {
  startSession: apiAdapter.sessions.start,
  getSession: apiAdapter.sessions.get,
  listSessions: apiAdapter.sessions.list,
  deleteSession: apiAdapter.sessions.delete,
  createCalibration: apiAdapter.calibration.create,
  getCalibration: apiAdapter.calibration.get,
  submitCalibration: apiAdapter.calibration.submit,
  postGaze: apiAdapter.metrics.gaze,
  postPose: apiAdapter.metrics.pose,
  postStress: apiAdapter.metrics.stress,
  postProductivity: apiAdapter.metrics.productivity,
  getDashboardSummary: apiAdapter.dashboard.summary,
  getAnalyticsTrends: apiAdapter.analytics.trends,
  runPipeline: apiAdapter.pipeline.process,
  config: apiAdapter.config,
  getSystemInfo: apiAdapter.system.getInfo,
  versions: apiAdapter.system.versions
});

contextBridge.exposeInMainWorld('wsConfig', {
  getBaseUrl: () => state.wsBase,
  setBaseUrl: (url) => {
    state.wsBase = url.replace(/\/$/, '');
  }
});

contextBridge.exposeInMainWorld('performance', {
  getResourceUsage: () => ({
    memory: process.memoryUsage?.() || null,
    cpuUsage: process.cpuUsage?.() || null
  }),
  requestGC: () => {
    if (global.gc) {
      global.gc();
      return true;
    }
    return false;
  }
});
