import { motion } from "framer-motion";
import { Database, Plus, PanelLeft, User } from "lucide-react";
import type { Message } from "@/app/types";

interface SidebarProps {
  isOpen: boolean;
  messages: Message[];
  onClose: () => void;
  onNewChat: () => void;
}

export default function Sidebar({ isOpen, messages, onClose, onNewChat }: SidebarProps) {
  const firstUserMessage = messages.find((m) => m.role === "user")?.content;

  return (
    <motion.aside
      initial={false}
      animate={{ width: isOpen ? 280 : 0, opacity: isOpen ? 1 : 0 }}
      className="relative flex flex-col h-full bg-sidebar-bg border-r border-border-custom overflow-hidden z-20"
    >
      <div className="flex items-center justify-between p-4 border-b border-border-custom h-[60px]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <Database className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-sm tracking-tight">PostgreSQL AI</span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-zinc-800 rounded-lg transition-colors"
          aria-label="Close sidebar"
        >
          <PanelLeft className="w-4 h-4 text-zinc-400" />
        </button>
      </div>

      <div className="p-3 flex-1 overflow-y-auto">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2.5 px-4 py-2.5 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 rounded-xl text-sm font-medium transition-all group"
        >
          <Plus className="w-4 h-4 text-zinc-400 group-hover:text-blue-400" />
          <span>Nouveau chat</span>
        </button>

        <div className="mt-8">
          <h3 className="px-4 text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-4">
            Récent
          </h3>
          <div className="space-y-1 px-4">
            {messages.length === 0 ? (
              <p className="text-xs text-zinc-600 italic">Aucune conversation</p>
            ) : (
              <p className="text-xs text-zinc-400 truncate">
                {firstUserMessage ?? "Conversation en cours"}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-border-custom bg-black/20">
        <div className="flex items-center gap-3 p-2 rounded-xl">
          <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center">
            <User className="w-4 h-4 text-zinc-400" />
          </div>
          <p className="text-sm font-medium text-zinc-300 truncate">Utilisateur</p>
        </div>
      </div>
    </motion.aside>
  );
}
