import { useMemo } from "react";
import { motion } from "motion/react";

interface ProgressiveMarkdownRevealProps {
  markdown: string;
  className?: string;
}

export function ProgressiveMarkdownReveal({
  markdown,
  className = "bg-black rounded-xl border border-[#262626] p-5 font-mono text-xs text-neutral-300 leading-relaxed whitespace-pre-wrap selection:bg-white selection:text-black",
}: ProgressiveMarkdownRevealProps) {
  // Split markdown by major sections (--- or headers) for staged progressive reveal
  const sections = useMemo(() => {
    if (!markdown) return [];
    const parts = markdown.split(/\n(?=#[^#])/g);
    return parts.filter(Boolean);
  }, [markdown]);

  if (sections.length <= 1) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className={className}
      >
        {markdown}
      </motion.div>
    );
  }

  return (
    <div className={className}>
      {sections.map((section, idx) => (
        <motion.div
          key={idx}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.2,
            delay: Math.min(idx * 0.05, 0.35),
            ease: "easeOut",
          }}
          className={idx > 0 ? "mt-4 pt-3 border-t border-[#181818]" : ""}
        >
          {section}
        </motion.div>
      ))}
    </div>
  );
}
