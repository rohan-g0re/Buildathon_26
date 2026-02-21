"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

interface MarkdownRendererProps {
  content: string;
  className?: string;
  compact?: boolean;
}

export function MarkdownRenderer({ content, className, compact }: MarkdownRendererProps) {
  return (
    <div
      className={cn(
        "markdown-body text-white/70 leading-relaxed",
        compact ? "text-xs md:text-sm" : "text-sm",
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg font-bold text-white/90 mt-4 mb-2 first:mt-0">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-semibold text-white/85 mt-3 mb-1.5 first:mt-0">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-white/80 mt-2.5 mb-1 first:mt-0">{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-sm font-medium text-white/75 mt-2 mb-1 first:mt-0">{children}</h4>
          ),
          p: ({ children }) => (
            <p className="mb-2 last:mb-0">{children}</p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white/90">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-white/60">{children}</em>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside mb-2 space-y-0.5 ml-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside mb-2 space-y-0.5 ml-1">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="text-white/65">{children}</li>
          ),
          a: ({ href, children }) => (
            <a href={href} className="text-blue-400 hover:text-blue-300 underline underline-offset-2" target="_blank" rel="noopener noreferrer">{children}</a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-white/20 pl-3 my-2 text-white/50 italic">{children}</blockquote>
          ),
          code: ({ className: codeClassName, children, ...props }) => {
            const isInline = !codeClassName;
            if (isInline) {
              return (
                <code className="bg-white/10 text-emerald-300/80 px-1.5 py-0.5 rounded text-[0.85em] font-mono" {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code className={cn("block bg-black/40 border border-white/[0.06] rounded-lg p-3 my-2 text-xs font-mono text-white/60 overflow-x-auto", codeClassName)} {...props}>
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="bg-black/40 border border-white/[0.06] rounded-lg p-3 my-2 overflow-x-auto">{children}</pre>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-2">
              <table className="w-full text-xs border-collapse">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="border-b border-white/10">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="text-left px-2 py-1.5 text-white/60 font-semibold text-[10px] uppercase tracking-wider">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-2 py-1.5 text-white/50 border-b border-white/[0.04]">{children}</td>
          ),
          hr: () => (
            <hr className="border-white/[0.08] my-3" />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
