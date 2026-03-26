import { useRef, useCallback, useEffect } from 'react';

export interface UseWebSocketOptions {
  url: string;
  onData: (data: unknown) => void;
  enabled?: boolean;
}

export function useWebSocket({ url, onData, enabled = false }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onDataRef = useRef(onData);
  onDataRef.current = onData;

  const cleanup = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connectWs = useCallback(() => {
    cleanup();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onDataRef.current(data);
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      reconnectTimer.current = setTimeout(connectWs, 1000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url, cleanup]);

  useEffect(() => {
    if (enabled) {
      connectWs();
    } else {
      cleanup();
    }
    return cleanup;
  }, [enabled, connectWs, cleanup]);
}
