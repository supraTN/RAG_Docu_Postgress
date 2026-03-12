import ReactMarkdown from "react-markdown";
import { Database, ExternalLink } from "lucide-react";
import CodeBlock from "./CodeBlock";

interface AIMessageProps {
  content: string;
  sources?: string[];
  latency?: number;
}

function getSourceLabel(url: string, index: number): string {
  try {
    const u = new URL(url);
    const segment = u.pathname
      .split("/")
      .filter(Boolean)
      .pop()
      ?.replace(/\.html$/, "")
      .replace(/-/g, " ");
    return segment || `Source ${index + 1}`;
  } catch {
    return `Source ${index + 1}`;
  }
}

export default function AIMessage({ content, sources, latency }: AIMessageProps) {
  return (
    <div className="flex gap-4 mb-8">
      <div className="shrink-0 flex items-center justify-center w-9 h-9 rounded-xl bg-zinc-900 border border-zinc-800 shadow-sm mt-1">
        <Database className="w-5 h-5 text-blue-500" />
      </div>

      <div className="flex-1 space-y-4 min-w-0">
        <div className="text-[15px] leading-relaxed text-zinc-200">
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
              ul: ({ children }) => (
                <ul className="list-disc list-outside ml-5 space-y-2 mb-4 text-zinc-300">
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-outside ml-5 space-y-2 mb-4 text-zinc-300">
                  {children}
                </ol>
              ),
              li: ({ children }) => <li className="pl-1">{children}</li>,
              strong: ({ children }) => (
                <strong className="text-white font-semibold">{children}</strong>
              ),
              h1: ({ children }) => (
                <h1 className="text-xl font-bold text-white mb-4 mt-6">{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-lg font-bold text-white mb-3 mt-5">{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-md font-semibold text-white mb-2 mt-4">{children}</h3>
              ),
              code: ({ children, className }) => {
                const isBlock = /language-(\w+)/.test(className || "");
                if (!isBlock) {
                  return (
                    <code className="bg-zinc-800 px-1.5 py-0.5 rounded text-[13px] font-mono text-blue-300 border border-zinc-700/50">
                      {children}
                    </code>
                  );
                }
                return (
                  <CodeBlock className={className}>{String(children)}</CodeBlock>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
        </div>

        {((sources && sources.length > 0) || latency !== undefined) && (
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-zinc-900">
            {sources && sources.length > 0 && (
              <>
                <span className="text-xs font-medium text-zinc-500 mr-1 uppercase tracking-wider">
                  Sources :
                </span>
                {sources.map((src, i) => (
                  <a
                    key={i}
                    href={src}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={src}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-blue-400 hover:text-blue-300 hover:bg-zinc-800 transition-all truncate max-w-[200px]"
                  >
                    <ExternalLink className="w-3 h-3 shrink-0" />
                    <span className="truncate">{getSourceLabel(src, i)}</span>
                  </a>
                ))}
              </>
            )}
            {latency !== undefined && (
              <span className="ml-auto text-xs font-mono text-zinc-600">
                {Math.round(latency)}ms
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
