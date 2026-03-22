import type { ThesisResult } from "@/types/api";

interface ThesisCardProps {
  thesis: ThesisResult;
  isLoading?: boolean;
}

const signalStyle = (signal: string) => {
  if (signal === "BULLISH" || signal === "POSITIVE")
    return { bg: "rgba(0,214,143,0.15)", border: "rgba(0,214,143,0.3)", color: "#00D68F" };
  if (signal === "BEARISH" || signal === "NEGATIVE")
    return { bg: "rgba(224,85,85,0.15)", border: "rgba(224,85,85,0.3)", color: "#E05555" };
  return { bg: "rgba(136,146,164,0.15)", border: "rgba(136,146,164,0.3)", color: "#8892A4" };
};

const confStyle = (c: string) => {
  if (c === "HIGH") return { color: "#00D68F" };
  if (c === "MEDIUM") return { color: "#F0A500" };
  return { color: "#E05555" };
};

const verdictConfig: Record<string, { icon: string; color: string; bg: string; border: string }> = {
  HOLD: { icon: "✓", color: "#00D68F", bg: "rgba(0,214,143,0.08)", border: "rgba(0,214,143,0.3)" },
  WATCH: { icon: "👁", color: "#F0A500", bg: "rgba(240,165,0,0.08)", border: "rgba(240,165,0,0.3)" },
  AVOID: { icon: "⚠", color: "#E05555", bg: "rgba(224,85,85,0.08)", border: "rgba(224,85,85,0.3)" },
};

const staggerDelays = [0, 50, 100, 150, 200];

const ThesisCard = ({ thesis, isLoading }: ThesisCardProps) => {
  if (isLoading) {
    return (
      <div style={{ background: "#0F1820", border: "1px solid #1E2D40", borderRadius: 12, overflow: "hidden" }}>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              height: 60,
              background: "linear-gradient(90deg, #1E2D40 25%, #253548 50%, #1E2D40 75%)",
              backgroundSize: "200% 100%",
              animation: "shimmer 1.5s infinite",
              margin: i < 2 ? "0 0 8px" : 0,
            }}
          />
        ))}
      </div>
    );
  }

  const conf = confStyle(thesis.confidence);
  const verdict = verdictConfig[thesis.verdict] || verdictConfig.WATCH;

  const signals = [
    {
      icon: "📊",
      label: "Fundamental",
      signal: thesis.fundamental.signal,
      reason: thesis.fundamental.reason,
      citation: thesis.fundamental.citation,
    },
    {
      icon: "📈",
      label: "Technical",
      signal: thesis.technical.signal,
      reason: thesis.technical.reason,
      citation: thesis.technical.rsi != null ? `RSI: ${thesis.technical.rsi}` : undefined,
    },
    {
      icon: "📰",
      label: "Sentiment",
      signal: thesis.sentiment.signal,
      reason: thesis.sentiment.reason,
      citation: thesis.sentiment.score != null ? `Score: ${thesis.sentiment.score.toFixed(2)}` : undefined,
    },
  ];

  return (
    <div
      className="inflect-card"
      style={{
        background: "#0F1820",
        border: "1px solid #1E2D40",
        borderRadius: 12,
        overflow: "hidden",
        animation: "bubbleIn 300ms ease-out",
      }}
    >
      {/* Header */}
      <div
        className="flex justify-between items-center"
        style={{ padding: "16px 20px", borderBottom: "1px solid #1E2D40" }}
      >
        <div>
          <p className="font-mono" style={{ color: "#F0A500", fontSize: 16, fontWeight: 700 }}>
            {thesis.ticker}
          </p>
          <p style={{ color: "white", fontSize: 12, marginTop: 2 }}>Trade Thesis</p>
        </div>
        <span
          className="font-mono"
          style={{
            fontSize: 11,
            color: conf.color,
            background: conf.color === "#00D68F" ? "rgba(0,214,143,0.15)" : conf.color === "#F0A500" ? "rgba(240,165,0,0.15)" : "rgba(224,85,85,0.15)",
            border: `1px solid ${conf.color}33`,
            borderRadius: 12,
            padding: "4px 10px",
          }}
        >
          ● {thesis.confidence} CONFIDENCE
        </span>
      </div>

      {/* Signal rows */}
      {signals.map((row, i) => {
        const s = signalStyle(row.signal);
        const isInsufficient = !row.reason;
        return (
          <div
            key={row.label}
            className="flex justify-between items-start"
            style={{
              padding: "14px 20px",
              gap: 16,
              borderBottom: "1px solid rgba(30,45,64,0.6)",
              animation: `thesisRowIn 300ms ease-out ${staggerDelays[i + 1]}ms both`,
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ color: "#8892A4", fontSize: 12 }}>
                {row.icon} {row.label}
              </p>
              <p style={{ color: "white", fontSize: 13, lineHeight: 1.5, marginTop: 4 }}>
                {isInsufficient ? "Not enough data available" : row.reason}
              </p>
              {row.citation && !isInsufficient && (
                <span
                  className="font-mono inline-block"
                  style={{
                    marginTop: 6,
                    background: "rgba(0,214,143,0.08)",
                    border: "1px solid rgba(0,214,143,0.3)",
                    color: "#00D68F",
                    borderRadius: 8,
                    padding: "2px 8px",
                    fontSize: 10,
                  }}
                >
                  📎 {row.citation}
                </span>
              )}
            </div>
            <span
              className="font-mono shrink-0"
              style={{
                fontSize: 11,
                background: isInsufficient ? "rgba(136,146,164,0.15)" : s.bg,
                border: `1px solid ${isInsufficient ? "rgba(136,146,164,0.3)" : s.border}`,
                color: isInsufficient ? "#8892A4" : s.color,
                borderRadius: 8,
                padding: "4px 10px",
              }}
            >
              {isInsufficient ? "INSUFFICIENT DATA" : row.signal}
            </span>
          </div>
        );
      })}

      {/* Verdict */}
      <div
        className="flex items-center gap-3"
        style={{
          padding: "16px 20px",
          background: verdict.bg,
          borderTop: `1px solid ${verdict.border}`,
          animation: `thesisRowIn 300ms ease-out ${staggerDelays[4]}ms both`,
        }}
      >
        <span style={{ fontSize: 18 }}>{verdict.icon}</span>
        <span style={{ color: verdict.color, fontSize: 18, fontWeight: 700 }}>{thesis.verdict}</span>
      </div>

      {/* Disclaimer */}
      <div
        style={{
          padding: "12px 20px",
          background: "rgba(8,12,20,0.5)",
          textAlign: "center",
          color: "#8892A4",
          fontSize: 11,
        }}
      >
        ⚠️ Educational only. Not investment advice.
      </div>
    </div>
  );
};

export default ThesisCard;
