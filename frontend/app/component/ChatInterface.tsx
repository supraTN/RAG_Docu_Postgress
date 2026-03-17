"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, PanelLeft } from "lucide-react";
import { useChat } from "@/app/hooks/useChat";
import Sidebar from "./Sidebar";
import ChatInput from "./ChatInput";
import WelcomeScreen from "./WelcomeScreen";
import UserMessage from "./UserMessage";
import AIMessage from "./AIMessage";
import LoadingBubble from "./LoadingBubble";

export default function ChatInterface() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const {
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
  } = useChat();

  return (
    <div className="flex h-screen overflow-hidden bg-black text-white selection:bg-blue-500/30">
      <Sidebar
        isOpen={isSidebarOpen}
        messages={messages}
        onClose={() => setIsSidebarOpen(false)}
        onNewChat={startNewChat}
      />

      <main className="flex-1 flex flex-col h-full bg-chat-bg relative">
        {!isSidebarOpen && (
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="absolute top-4 left-4 p-2 hover:bg-zinc-900 rounded-lg transition-colors z-30 bg-black border border-zinc-800"
            aria-label="Open sidebar"
          >
            <PanelLeft className="w-5 h-5 text-zinc-400" />
          </button>
        )}

        <header className="flex items-center px-8 h-[60px] border-b border-border-custom glass-header sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-semibold text-emerald-500/80 tracking-wide uppercase">
              RAG System Active
            </span>
          </div>
          <ChevronRight className="w-3 h-3 text-zinc-700 mx-3" />
          <span className="text-xs font-medium text-zinc-400">
            PostgreSQL Docs · v16
          </span>
        </header>

        <div className="flex-1 overflow-y-auto scroll-smooth">
          <div className="max-w-4xl mx-auto px-6 py-10">
            {messages.length === 0 && !isLoading ? (
              <WelcomeScreen onSelect={sendMessage} />
            ) : (
              <div className="space-y-6">
                <AnimatePresence initial={false}>
                  {messages.map((msg) => (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      {msg.role === "user" ? (
                        <UserMessage content={msg.content} />
                      ) : (
                        <AIMessage
                          content={msg.content}
                          sources={msg.sources}
                          latency={msg.latency}
                        />
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>

                {isLoading && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <LoadingBubble />
                  </motion.div>
                )}

                <div ref={messagesEndRef} className="h-4" />
              </div>
            )}
          </div>
        </div>

        <ChatInput
          input={input}
          isLoading={isLoading}
          model={model}
          textareaRef={textareaRef}
          onChange={setInput}
          onModelChange={setModel}
          onSend={() => sendMessage(input)}
        />
      </main>
    </div>
  );
}
