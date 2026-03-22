import type { AnswerResult } from "@/types/api";

interface ChatBubbleProps {
  role: "user" | "assistant";
  content: string;
  answerData?: AnswerResult;
  isLoading?: boolean;
  timestamp: string;
}

const sourceBadges: Record<string, { emoji: string; label: string; color: string; bg: string; border: string }> = {
  SEC_FILING: { emoji: "📎", label: "SEC Filing", color: "#00D68F", bg: "rgba(0,214,143,0.1)", border: "rgba(0,214,143,0.3)" },
  WOLFRAM: { emoji: "⚡", label: "Wolfram|Alpha", color: "#F0A500", bg: "rgba(240,165,0,0.1)", border: "rgba(240,165,0,0.3)" },
  MARKET_DATA: { emoji: "📊", label: "Market Data", color: "#00C8FF", bg: "rgba(0,200,255,0.1)", border: "rgba(0,200,255,0.3)" },
  LLM: { emoji: "🤖", label: "AI Analysis", color: "#8892A4", bg: "rgba(136,146,164,0.1)", border: "rgba(136,146,164,0.3)" },
};

const confidenceColors: Record<string, string> = {
  HIGH: "#00D68F",
  MEDIUM: "#F0A500",
  LOW: "#E05555",
};

const ChatBubble = ({ role, content, answerData, isLoading, timestamp }: ChatBubbleProps) => {
  if (isLoading) {
    return (
      <div className="flex justify-start" style={{ animation: "bubbleIn 200ms ease-out" }}>
        <div
          className="flex items-center gap-1.5"
          style={{
            background: "#0F1820",
            border: "1px solid #1E2D40",
            borderRadius: "12px 12px 12px 2px",
            padding: "16px 20px",
          }}
        >
          {[0, 150, 300].map((delay) => (
            <div
              key={delay}
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "#F0A500",
                animation: `chatBounce 0.6s ease-in-out ${delay}ms infinite`,
              }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (role === "user") {
    return (
      <div className="flex justify-end" style={{ animation: "bubbleIn 200ms ease-out" }}>
        <div
          style={{
            maxWidth: "75%",
            background: "rgba(240,165,0,0.1)",
            border: "1px solid rgba(240,165,0,0.2)",
            borderRadius: "12px 12px 2px 12px",
            padding: "12px 16px",
            color: "white",
            fontSize: 14,
            lineHeight: 1.5,
          }}
        >
          {content}
        </div>
      </div>
    );
  }

  // Assistant bubble
  const badge = answerData ? sourceBadges[answerData.source] : null;
  const confColor = answerData ? confidenceColors[answerData.confidence] : null;

  return (
    <div className="flex justify-start" style={{ animation: "bubbleIn 200ms ease-out" }}>
      <div
        style={{
          maxWidth: "85%",
          background: "#0F1820",
          border: "1px solid #1E2D40",
          borderRadius: "12px 12px 12px 2px",
          padding: 16,
        }}
      >
        <p style={{ color: "white", fontSize: 14, lineHeight: 1.6, marginBottom: answerData ? 12 : 0, whiteSpace: "pre-wrap" }}>
          {content}
        </p>

        {answerData && (
          <div>
            {/* Source badge */}
            {badge && (
              <div className="flex gap-2 flex-wrap">
                <span
                  className="font-mono"
                  style={{
                    background: badge.bg,
                    border: `1px solid ${badge.border}`,
                    color: badge.color,
                    borderRadius: 12,
                    padding: "4px 10px",
                    fontSize: 11,
                  }}
                >
                  {badge.emoji} {badge.label}
                </span>
              </div>
            )}

            {/* Citation */}
            {answerData.citation && (
              <p className="font-mono" style={{ color: "#8892A4", fontSize: 11, marginTop: 8 }}>
                {answerData.citation}
              </p>
            )}

            {/* Confidence */}
            {confColor && (
              <div className="flex items-center gap-1.5" style={{ marginTop: 8 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: confColor }} />
                <span className="font-mono" style={{ color: confColor, fontSize: 11 }}>
                  {answerData.confidence} Confidence
                </span>
              </div>
            )}

            {/* Action chips */}
            <div className="flex gap-2 flex-wrap" style={{ marginTop: 12 }}>
              {answerData.intent_type === "research" && (
                <button
                  className="transition-colors duration-150"
                  style={{
                    border: "1px solid rgba(240,165,0,0.4)",
                    background: "transparent",
                    borderRadius: 16,
                    padding: "6px 14px",
                    color: "#F0A500",
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(240,165,0,0.1)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  Generate Thesis →
                </button>
              )}
              {answerData.ticker && (
                <button
                  className="transition-colors duration-150"
                  style={{
                    border: "1px solid rgba(240,165,0,0.4)",
                    background: "transparent",
                    borderRadius: 16,
                    padding: "6px 14px",
                    color: "#F0A500",
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(240,165,0,0.1)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  Plot Trend →
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatBubble;
