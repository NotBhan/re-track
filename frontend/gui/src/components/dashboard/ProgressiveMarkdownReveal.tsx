import { useMemo } from "react";
import { motion } from "motion/react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

interface ProgressiveMarkdownRevealProps {
  markdown: string;
  className?: string;
}

const markdownComponents = {
  h1: ({ node, ...props }: any) => (
    <h1 className="text-sm font-bold text-white border-b border-[#1e1e1e] pb-1.5 mb-2.5 mt-4 first:mt-0 tracking-tight" {...props} />
  ),
  h2: ({ node, ...props }: any) => (
    <h2 className="text-xs font-semibold text-neutral-100 border-b border-[#181818] pb-1 mb-2 mt-3.5 first:mt-0 tracking-tight flex items-center gap-1.5" {...props} />
  ),
  h3: ({ node, ...props }: any) => (
    <h3 className="text-xs font-semibold text-neutral-200 mb-1.5 mt-3 first:mt-0 tracking-tight" {...props} />
  ),
  h4: ({ node, ...props }: any) => (
    <h4 className="text-xs font-medium text-neutral-300 mb-1 mt-2" {...props} />
  ),
  p: ({ node, ...props }: any) => (
    <p className="text-xs text-neutral-300 font-sans leading-relaxed mb-2.5 last:mb-0" {...props} />
  ),
  ul: ({ node, ...props }: any) => (
    <ul className="list-disc pl-4 space-y-1 mb-2.5 text-xs text-neutral-300 font-sans" {...props} />
  ),
  ol: ({ node, ...props }: any) => (
    <ol className="list-decimal pl-4 space-y-1 mb-2.5 text-xs text-neutral-300 font-sans" {...props} />
  ),
  li: ({ node, ...props }: any) => (
    <li className="leading-relaxed text-xs text-neutral-300 font-sans" {...props} />
  ),
  code: ({ node, className, children, ...props }: any) => {
    return (
      <code
        className="font-mono text-[11px] bg-[#121212] border border-[#222222] text-neutral-200 px-1 py-0.5 rounded selection:bg-white selection:text-black"
        {...props}
      >
        {children}
      </code>
    );
  },
  pre: ({ node, children, ...props }: any) => (
    <pre
      className="bg-[#050505] border border-[#1e1e1e] rounded-md p-3 my-2.5 overflow-x-auto font-mono text-xs text-neutral-200 leading-relaxed selection:bg-white selection:text-black [&>code]:bg-transparent [&>code]:border-0 [&>code]:p-0"
      {...props}
    >
      {children}
    </pre>
  ),
  blockquote: ({ node, ...props }: any) => (
    <blockquote className="border-l-2 border-neutral-600 pl-3 py-0.5 text-xs text-neutral-400 font-sans my-2 italic" {...props} />
  ),
  hr: ({ node, ...props }: any) => (
    <hr className="border-[#1e1e1e] my-3.5" {...props} />
  ),
  table: ({ node, ...props }: any) => (
    <div className="overflow-x-auto my-3 rounded-md border border-[#1e1e1e]">
      <table className="w-full text-xs font-mono border-collapse" {...props} />
    </div>
  ),
  thead: ({ node, ...props }: any) => (
    <thead className="bg-[#080808] border-b border-[#1e1e1e] text-neutral-300 font-medium" {...props} />
  ),
  th: ({ node, ...props }: any) => (
    <th className="px-3 py-1.5 text-left font-medium border-r border-[#1a1a1a] last:border-r-0 text-neutral-200" {...props} />
  ),
  td: ({ node, ...props }: any) => (
    <td className="px-3 py-1.5 border-t border-r border-[#141414] last:border-r-0 text-neutral-300" {...props} />
  ),
  tr: ({ node, ...props }: any) => (
    <tr className="hover:bg-[#0c0c0c] transition-colors" {...props} />
  ),
  strong: ({ node, ...props }: any) => (
    <strong className="font-semibold text-white" {...props} />
  ),
  em: ({ node, ...props }: any) => (
    <em className="italic text-neutral-200" {...props} />
  ),
};

export function ProgressiveMarkdownReveal({
  markdown,
  className,
}: ProgressiveMarkdownRevealProps) {
  // Split markdown by major sections (--- or headers) for staged progressive reveal
  const sections = useMemo(() => {
    if (!markdown) return [];
    const parts = markdown.split(/\n(?=#[^#])/g);
    return parts.filter(Boolean);
  }, [markdown]);

  const containerCls = cn(
    "bg-[#050505] rounded-lg border border-[#1a1a1a] p-4 text-xs text-neutral-300 leading-relaxed selection:bg-white selection:text-black",
    className
  );

  if (sections.length <= 1) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className={containerCls}
      >
        <ReactMarkdown components={markdownComponents}>{markdown}</ReactMarkdown>
      </motion.div>
    );
  }

  return (
    <div className={containerCls}>
      {sections.map((section, idx) => (
        <motion.div
          key={idx}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.18,
            delay: Math.min(idx * 0.04, 0.25),
            ease: "easeOut",
          }}
          className={idx > 0 ? "mt-3.5 pt-3 border-t border-[#141414]" : ""}
        >
          <ReactMarkdown components={markdownComponents}>{section}</ReactMarkdown>
        </motion.div>
      ))}
    </div>
  );
}
