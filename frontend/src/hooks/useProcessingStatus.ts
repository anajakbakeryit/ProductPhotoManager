import { useEffect, useRef, useState, useCallback } from 'react';

interface ProcessingMessage {
  type: 'processing_start' | 'processing_done' | 'processing_error';
  photo_id: number;
  barcode: string;
  filename?: string;
  status?: string;
  has_cutout?: boolean;
  has_watermark?: boolean;
}

export function useProcessingStatus() {
  const [messages, setMessages] = useState<ProcessingMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/processing`);

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const msg: ProcessingMessage = JSON.parse(event.data);
        setMessages((prev) => [...prev.slice(-50), msg]);
      } catch {
        // ignore non-JSON messages
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Auto-reconnect after 3s
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { messages, isConnected, lastMessage: messages[messages.length - 1] || null };
}
