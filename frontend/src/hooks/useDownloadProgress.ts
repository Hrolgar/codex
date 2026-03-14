import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { DownloadResponse } from "@/api/client";

interface DownloadMessage {
  id: string;
  status: string;
  progress: number;
}

export function useDownloadProgress() {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/downloads`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const msg: DownloadMessage = JSON.parse(event.data);
          queryClient.setQueriesData<DownloadResponse[]>(
            { queryKey: ["downloads"] },
            (old) => {
              if (!old) return old;
              return old.map((d) =>
                d.id === msg.id
                  ? { ...d, status: msg.status, progress: msg.progress }
                  : d
              );
            }
          );
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        reconnectTimer.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [queryClient]);
}
