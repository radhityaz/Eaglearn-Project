# Frontend API Call Map

This document maps frontend API calls to backend endpoints as defined in the specifications.

## IPC Calls from Frontend

All calls are made via Electron's IPC mechanism (`ipcRenderer.invoke`) to the backend.

### 1. [frontend/renderer.js:376](frontend/renderer.js:376)

- **Method**: `ipcRenderer.invoke`
- **Channel**: `"send-to-backend"`
- **Payload**: `{type: 'UPDATE_SETTINGS', settings}`
- **Mapped Spec Endpoint**: Not applicable (No HTTP endpoint, uses IPC)
- **Notes**: This call sends user settings updates to the backend via IPC channel.
  - The payload structure does not map directly to any REST API endpoint in [spec/45_api_contracts.md](spec/45_api_contracts.md:36).
  - The `type` field suggests it's part of a protocol, not an HTTP API call.

### 2. [frontend/preload.js:14](frontend/preload.js:14)

- **Method**: `ipcRenderer.invoke`
- **Channel**: `"send-to-backend"`
- **Payload**: `{type: 'GET_SYSTEM_INFO'}`
- **Mapped Spec Endpoint**: Not applicable (No HTTP endpoint, uses IPC)
- **Notes**: This call retrieves system info from the backend via IPC channel.
  - The payload structure does not map directly to any REST API endpoint in [spec/45_api_contracts.md](spec/45_api_contracts.md:36).
  - The `type` field suggests it's part of a protocol, not an HTTP API call.

### 3. [frontend/preload.js:11](frontend/preload.js:11)

- **Method**: `ipcRenderer.invoke`
- **Channel**: `"get-system-info"`
- **Payload**: `{}`
- **Mapped Spec Endpoint**: Not applicable (No HTTP endpoint, uses IPC)
- **Notes**: This call retrieves system info from the backend via IPC channel.
  - The payload is empty.
  - The `channel` name does not map to any REST API endpoint in [spec/45_api_contracts.md](spec/45_api_contracts.md:36).
  - The `type` field suggests it's part of a protocol, not an HTTP API call.

### 4. [frontend/preload.js:17](frontend/preload.js:17)

- **Method**: `ipcRenderer.invoke`
- **Channel**: `"open-settings"`
- **Payload**: `{}`
- **Mapped Spec Endpoint**: Not applicable (No HTTP endpoint, uses IPC)
- **Notes**: This call opens the settings dialog in the frontend.
  - The payload is empty.
  - The `channel` name does not map to any REST API endpoint in [spec/45_api_contracts.md](spec/45_api_contracts.md:36).
  - The `type` field suggests it's part of a protocol, not an HTTP API call.
