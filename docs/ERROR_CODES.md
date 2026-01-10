# Error Codes

Semua response error REST API menggunakan format:

```json
{
  "status": "error",
  "error_code": "SOME_CODE",
  "message": "Human readable message"
}
```

## Daftar

- `ENVIRONMENT_ERROR`
- `SESSION_START_ERROR`
- `SESSION_STOP_ERROR`
- `WEBCAM_START_FAILED`
- `METRICS_LOG_NOT_AVAILABLE`
- `METRICS_LOG_DOWNLOAD_ERROR`
- `QUALITY_SET_ERROR`
- `BAD_REQUEST`
- `NOT_FOUND`
- `INTERNAL_ERROR`
