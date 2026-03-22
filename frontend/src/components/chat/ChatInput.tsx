import { useState, useRef, useCallback, useEffect } from "react";

interface ChatInputProps {
  onSubmit: (text: string) => void;
  disabled: boolean;
  placeholder?: string;
}

const ChatInput = ({ onSubmit, disabled, placeholder = "Ask anything about a stock..." }: ChatInputProps) => {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const canSubmit = value.trim().length > 0 && !disabled;

  // Auto-grow textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }, [value]);

  const handleSubmit = useCallback(() => {
    if (!canSubmit) return;
    onSubmit(value.trim());
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [canSubmit, value, onSubmit]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div style={{ padding: "16px 24px", borderTop: "1px solid #1E2D40", background: "#0F1820" }}>
      <div
        ref={wrapperRef}
        className="flex items-center gap-3 transition-colors duration-200"
        style={{
          background: "#080C14",
          border: "1px solid #1E2D40",
          borderRadius: 12,
          padding: "12px 16px",
        }}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          className="flex-1 focus:outline-none"
          style={{
            background: "transparent",
            border: "none",
            color: "white",
            fontSize: 14,
            resize: "none",
            maxHeight: 120,
            overflowY: "auto",
            lineHeight: 1.5,
          }}
          onFocus={() => {
            if (wrapperRef.current) wrapperRef.current.style.borderColor = "#F0A500";
          }}
          onBlur={() => {
            if (wrapperRef.current) wrapperRef.current.style.borderColor = "#1E2D40";
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="shrink-0 flex items-center justify-center transition-colors duration-150"
          style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            background: "#F0A500",
            border: "none",
            cursor: canSubmit ? "pointer" : "not-allowed",
            opacity: canSubmit ? 1 : 0.4,
          }}
          onMouseEnter={(e) => {
            if (canSubmit) e.currentTarget.style.background = "#D4920A";
          }}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#F0A500")}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default ChatInput;
