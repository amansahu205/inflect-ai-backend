const sourceIcons: Record<string, string> = {
  SEC_FILING: "📎",
  WOLFRAM: "⚡",
  MARKET_DATA: "📊",
  LLM: "🤖",
};

interface CitationCardProps {
  citation: string;
  source: string;
}

const CitationCard = ({ citation, source }: CitationCardProps) => (
  <div
    className="flex items-center gap-2"
    style={{
      background: "rgba(0,214,143,0.04)",
      border: "1px solid rgba(0,214,143,0.2)",
      borderRadius: 8,
      padding: "10px 14px",
    }}
  >
    <span style={{ fontSize: 14 }}>{sourceIcons[source] || "📎"}</span>
    <span className="font-mono" style={{ color: "#8892A4", fontSize: 11 }}>
      {citation}
    </span>
  </div>
);

export default CitationCard;
