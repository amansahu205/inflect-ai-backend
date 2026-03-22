import { useRef, useEffect, useState } from "react";
import ChatBubble from "./ChatBubble";
import ThesisCard from "@/components/research/ThesisCard";
import type { AnswerResult, ThesisResult } from "@/types/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  answerData?: AnswerResult;
  thesisData?: ThesisResult;
  thesisLoading?: boolean;
  timestamp: string;
}

interface ChatThreadProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

const ChatThread = ({ messages, isLoading }: ChatThreadProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const scrollToBottom = () => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  };

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distFromBottom < 150) scrollToBottom();
  }, [messages.length, isLoading]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const handler = () => {
      const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      setShowScrollBtn(distFromBottom > 100);
    };
    el.addEventListener("scroll", handler, { passive: true });
    return () => el.removeEventListener("scroll", handler);
  }, []);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto relative" style={{ padding: 24 }}>
      <div className="flex flex-col gap-4">
        {messages.map((msg) => (
          <div key={msg.id}>
            <ChatBubble
              role={msg.role}
              content={msg.content}
              answerData={msg.answerData}
              timestamp={msg.timestamp}
            />
            {/* Inline ThesisCard in chat */}
            {(msg.thesisLoading || msg.thesisData) && (
              <div style={{ marginTop: 8, maxWidth: "85%" }}>
                <ThesisCard thesis={msg.thesisData!} isLoading={msg.thesisLoading} />
              </div>
            )}
          </div>
        ))}
        {isLoading && <ChatBubble role="assistant" content="" isLoading timestamp="" />}
      </div>

      {showScrollBtn && (
        <button
          onClick={scrollToBottom}
          className="fixed transition-colors duration-150"
          style={{
            bottom: 120,
            right: "calc(40% + 24px)",
            background: "#F0A500",
            color: "#080C14",
            borderRadius: 20,
            padding: "8px 16px",
            fontSize: 12,
            cursor: "pointer",
            zIndex: 10,
            fontWeight: 600,
            border: "none",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#D4920A")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#F0A500")}
        >
          ↓ New response
        </button>
      )}
    </div>
  );
};

export default ChatThread;
