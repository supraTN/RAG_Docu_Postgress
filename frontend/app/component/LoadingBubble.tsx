import { Database } from "lucide-react";

export default function LoadingBubble() {
  return (
    <div className="flex gap-4 mb-8">
      <div className="shrink-0 flex items-center justify-center w-9 h-9 rounded-xl bg-zinc-900 border border-zinc-800 mt-1">
        <Database className="w-5 h-5 text-blue-500" />
      </div>
      <div className="px-5 py-4 rounded-2xl rounded-tl-sm bg-zinc-900 border border-zinc-800 shadow-sm">
        <div className="flex gap-1.5 items-center">
          {[0, 200, 400].map((delay) => (
            <span
              key={delay}
              className="w-2 h-2 rounded-full bg-blue-500 dot-bounce"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
