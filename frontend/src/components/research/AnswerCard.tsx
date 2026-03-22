import { useState } from "react";
import CitationCard from "./CitationCard";

interface AnswerCardProps {
  answer: string;
  source: "SEC_FILING" | "WOLFRAM" | "MARKET_DATA" | "LLM";
  citation: string | null;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  ticker: string | null;
  onGenerateThesis: () => void;
  onPlotTrend: () => void;
}

const sourceBadges: Record<string, { emoji: string; label: string; color: string; bg: string; border: string }> = {
  SEC_FILING: { emoji: "📎", label: "SEC Filing", color: "#00D68F", bg: "rgba(0,214,143,0.08)", border: "rgba(0,214,143,0.3)" },
  WOLFRAM: { emoji: "⚡", label: "Wolfram|Alpha", color: "#F0A500", bg: "rgba(240,165,0,0.08)", border: "rgba(240,165,0,0.3)" },
  MARKET_DATA: { emoji: "📊", label: "Market Data", color: "#00C8FF", bg: "rgba(0,200,255,0.08)", border: "rgba(0,200,255,0.3)" },
  LLM: { emoji: "🤖", label: "AI Generated", color: "#8892A4", bg: "rgba(136,146,164,0.08)", border: "rgba(136,146,164,0.3)" },
};

const confStyles: Record<string, { color: string }> = {
  HIGH: { color: "#00D68F" },
  MEDIUM: { color: "#F0A500" },
  LOW: { color: "#E05555" },
};

const WORD_LIMIT = 200;

const AnswerCard = ({ answer, source, citation, confidence, ticker, onGenerateThesis, onPlotTrend }: AnswerCardProps) => {
  const [expanded, setExpanded] = useState(false);
  const badge = sourceBadges[source];
  const conf = confStyles[confidence];
  const words = answer.split(/\s+/);
  const isLong = words.length > WORD_LIMIT;
  const displayText = isLong && !expanded ? words.slice(0, WORD_LIMIT).join(" ") + "..." : answer;

  return (
    <div
      className="inflect-card"
      style={{
        background: "#0F1820",
        border: "1px solid #1E2D40",
        borderRadius: 12,
        padding: 20,
        animation: "answerSlideIn 300ms ease-out",
      }}
    >
      {/* Header */}
      <div className="flex justify-between items-center">
        <span style={{ color: "#8892A4", fontSize: 10, letterSpacing: "0.2em" }}>ANSWER</span>
        <div className="flex items-center gap-1.5">
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: conf.color }} />
          <span className="font-mono" style={{ color: conf.color, fontSize: 11 }}>{confidence}</span>
        </div>
      </div>

      {/* Low confidence warning */}
      {confidence === "LOW" && (
        <div
          style={{
            background: "rgba(240,165,0,0.08)",
            border: "1px solid rgba(240,165,0,0.2)",
            borderRadius: 6,
            padding: "8px 12px",
            marginTop: 12,
            color: "#F0A500",
            fontSize: 12,
          }}
        >
          ⚠️ Low confidence — verify independently
        </div>
      )}

      {/* Answer text */}
      <p style={{ color: "white", fontSize: 14, lineHeight: 1.7, margin: "12px 0", whiteSpace: "pre-wrap" }}>
        {displayText}
      </p>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          style={{ background: "none", border: "none", color: "#F0A500", fontSize: 13, cursor: "pointer", padding: 0 }}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}

      {/* Source badge */}
      {badge && (
        <div style={{ marginTop: 12 }}>
          <span
            className="font-mono"
            style={{
              background: badge.bg,
              border: `1px solid ${badge.border}`,
              color: badge.color,
              borderRadius: 12,
              padding: "4px 10px",
              fontSize: 11,
              display: "inline-block",
            }}
          >
            {badge.emoji} {badge.label}
          </span>
        </div>
      )}

      {/* Citation */}
      {citation && (
        <div style={{ marginTop: 10 }}>
          <CitationCard citation={citation} source={source} />
        </div>
      )}

      {/* Divider */}
      {ticker && <div style={{ height: 1, background: "#1E2D40", margin: "16px 0" }} />}

      {/* Action chips */}
      {ticker && (
        <div className="flex gap-2 flex-wrap">
          {["Generate Thesis →", "Plot Trend →"].map((label, i) => (
            <button
              key={label}
              onClick={i === 0 ? onGenerateThesis : onPlotTrend}
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
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(240,165,0,0.08)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default AnswerCard;
