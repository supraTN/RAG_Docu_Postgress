"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Clipboard, ClipboardCheck } from "lucide-react";

interface CodeBlockProps {
  children: string;
  className?: string;
}

export default function CodeBlock({ children, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const match = /language-(\w+)/.exec(className || "");
  const lang = match ? match[1] : "sql";

  function copyToClipboard() {
    navigator.clipboard.writeText(children.trim());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="relative my-4 rounded-xl overflow-hidden border border-zinc-800">
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-800/80 text-zinc-400 text-xs font-mono uppercase tracking-widest border-b border-zinc-800">
        <span>{lang}</span>
        <button
          onClick={copyToClipboard}
          className="hover:text-white transition-colors flex items-center gap-1.5"
        >
          {copied ? (
            <ClipboardCheck className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <Clipboard className="w-3.5 h-3.5" />
          )}
          {copied ? "Copié !" : "Copier"}
        </button>
      </div>
      <SyntaxHighlighter
        language={lang}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          padding: "1.25rem",
          background: "transparent",
          fontSize: "13px",
        }}
        codeTagProps={{ style: { fontFamily: "var(--font-mono)" } }}
      >
        {children.trim()}
      </SyntaxHighlighter>
    </div>
  );
}
