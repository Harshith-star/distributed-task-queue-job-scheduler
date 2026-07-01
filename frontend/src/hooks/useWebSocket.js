import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export function useTaskWebSocket(userId) {
  const ws          = useRef(null);
  const queryClient = useQueryClient();
  const reconnect   = useRef(null);

  const connect = useCallback(() => {
    if (!userId) return;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host     = window.location.hostname;
    const port     = import.meta.env.DEV ? '8000' : window.location.port;
    ws.current = new WebSocket(`${protocol}://${host}:${port}/api/v1/ws/${userId}`);

    ws.current.onopen  = () => console.log('[WS] Connected');
    ws.current.onclose = () => {
      console.log('[WS] Disconnected — reconnecting in 3s');
      reconnect.current = setTimeout(connect, 3000);
    };
    ws.current.onerror = (e) => console.warn('[WS] Error', e);
    ws.current.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'ping') return;
        if (msg.type === 'execution_update') {
          // Invalidate relevant queries so React Query re-fetches
          queryClient.invalidateQueries({ queryKey: ['executions'] });
          queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          queryClient.invalidateQueries({ queryKey: ['notifications'] });
        }
      } catch {}
    };
  }, [userId, queryClient]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnect.current);
      ws.current?.close();
    };
  }, [connect]);
}
