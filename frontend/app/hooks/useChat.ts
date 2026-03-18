"use client";

import { useState, useRef, useEffect } from "react";
import type { Message, ModelOption } from "@/app/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [model, setModel] = useState<ModelOption>("gpt-4.1-mini");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  }, [input]);

  async function sendMessage(question: string) {
    if (!question.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: question.trim(),
      timestamp: new Date(),
    };

    const aiMsgId = (Date.now() + 1).toString();

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    try {
      const response = await fetch(`${API_URL}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question.trim(), history, model }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      // Add empty AI message that we'll fill progressively
      setMessages((prev) => [
        ...prev,
        {
          id: aiMsgId,
          role: "ai",
          content: "",
          timestamp: new Date(),
        },
      ]);

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let payload: { type: string; content?: string; sources?: string[]; latency_ms?: number };
          try {
            payload = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          if (payload.type === "token") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiMsgId
                  ? { ...m, content: m.content + payload.content }
                  : m
              )
            );
          } else if (payload.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiMsgId
                  ? { ...m, sources: payload.sources, latency: payload.latency_ms }
                  : m
              )
            );
          }
        }
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          id: aiMsgId,
          role: "ai",
          content:
            "Connection error. Make sure the backend server is running on port 8000.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function startNewChat() {
    setMessages([]);
    setInput("");
  }

  return {
    messages,
    input,
    isLoading,
    model,
    setInput,
    setModel,
    sendMessage,
    startNewChat,
    messagesEndRef,
    textareaRef,
  };
}
