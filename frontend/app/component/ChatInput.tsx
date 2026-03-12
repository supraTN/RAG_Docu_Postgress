import { type KeyboardEvent, type RefObject } from "react";
import { Send, Loader2 } from "lucide-react";
import { cn } from "@/app/lib/utils";

interface ChatInputProps {
  input: string;
  isLoading: boolean;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  onChange: (value: string) => void;
  onSend: () => void;
}

export default function ChatInput({
  input,
  isLoading,
  textareaRef,
  onChange,
  onSend,
}: ChatInputProps) {
  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  }

  return (
    <div className="w-full bg-gradient-to-t from-black via-black/95 to-transparent pt-10 pb-8 px-6 sticky bottom-0">
      <div className="max-w-3xl mx-auto">
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-3xl opacity-0 group-focus-within:opacity-20 blur transition-opacity duration-500" />

          <div className="relative flex flex-col gap-2 bg-zinc-900 border border-border-custom rounded-3xl p-2.5 transition-all focus-within:border-zinc-700 shadow-2xl glass-input">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Posez votre question sur PostgreSQL..."
              rows={1}
              className="w-full bg-transparent px-4 py-3 text-[15px] text-white placeholder-zinc-500 focus:outline-none resize-none disabled:opacity-50 leading-relaxed min-h-[50px] max-h-[200px]"
            />
            <div className="flex items-center justify-end px-2 pb-1">
              <button
                onClick={onSend}
                disabled={isLoading || !input.trim()}
                aria-label="Envoyer"
                className={cn(
                  "flex items-center justify-center h-10 w-10 rounded-2xl transition-all",
                  "hover:scale-105 active:scale-95 disabled:opacity-20 disabled:scale-100 disabled:cursor-not-allowed",
                  input.trim() ? "bg-blue-600 text-white" : "bg-zinc-800 text-zinc-500"
                )}
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>
        <p className="text-center text-[11px] text-zinc-600 mt-4 font-medium tracking-wide">
          gpt-4.1-mini peut faire des erreurs. Vérifiez toujours la documentation officielle.
        </p>
      </div>
    </div>
  );
}
