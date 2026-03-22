import type { Query } from "@/types/api";

interface QueryHistoryProps {
  queries: Query[];
  onSelect: (query: Query) => void;
  activeQueryId: string | null;
  onClear?: () => void;
}

const intentBadge: Record<string, { label: string; color: string; bg: string; border: string }> = {
  research: { label: "RESEARCH", color: "#F0A500", bg: "rgba(240,165,0,0.12)", border: "rgba(240,165,0,0.3)" },
  price_check: { label: "PRICE", color: "#00C8FF", bg: "rgba(0,200,255,0.12)", border: "rgba(0,200,255,0.3)" },
  thesis: { label: "THESIS", color: "#00D68F", bg: "rgba(0,214,143,0.12)", border: "rgba(0,214,143,0.3)" },
  trade: { label: "TRADE", color: "#E05555", bg: "rgba(224,85,85,0.12)", border: "rgba(224,85,85,0.3)" },
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const QueryHistory = ({ queries, onSelect, activeQueryId, onClear }: QueryHistoryProps) => {
  return (
    <div
      style={{
        height: "100%",
        overflowY: "auto",
        padding: 16,
        background: "#0F1820",
      }}
    >
      {/* Title row */}
      <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
        <span style={{ color: "#8892A4", fontSize: 10, letterSpacing: "0.2em" }}>QUERY HISTORY</span>
        {queries.length > 0 && onClear && (
          <button
            onClick={onClear}
            className="transition-colors duration-150"
            style={{
              background: "none",
              border: "none",
              color: "#8892A4",
              fontSize: 11,
              cursor: "pointer",
              padding: 0,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#E05555")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#8892A4")}
          >
            Clear
          </button>
        )}
      </div>

      {/* Empty state */}
      {queries.length === 0 ? (
        <div style={{ padding: "40px 16px", textAlign: "center" }}>
          <p style={{ color: "#8892A4", fontSize: 13 }}>Your queries will appear here</p>
        </div>
      ) : (
        <div className="flex flex-col">
          {queries.map((q, i) => {
            const isActive = q.id === activeQueryId;
            const badge = intentBadge[q.intent_type] || intentBadge.research;
            return (
              <button
                key={q.id}
                onClick={() => onSelect(q)}
                className="text-left transition-all duration-150"
                style={{
                  padding: "10px 12px",
                  borderRadius: 8,
                  cursor: "pointer",
                  marginBottom: 4,
                  border: isActive ? "1px solid rgba(240,165,0,0.3)" : "1px solid transparent",
                  background: isActive ? "rgba(240,165,0,0.1)" : "transparent",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.background = "transparent";
                }}
              >
                {/* Query text */}
                <p
                  style={{
                    color: "white",
                    fontSize: 13,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    maxWidth: "100%",
                    margin: 0,
                  }}
                >
                  Q{queries.length - i}: {q.transcript?.slice(0, 40) || "..."}
                </p>

                {/* Intent badge + time */}
                <div className="flex justify-between items-center" style={{ marginTop: 4 }}>
                  <span
                    className="font-mono"
                    style={{
                      fontSize: 9,
                      padding: "2px 6px",
                      borderRadius: 6,
                      background: badge.bg,
                      border: `1px solid ${badge.border}`,
                      color: badge.color,
                    }}
                  >
                    {badge.label}
                  </span>
                  <span style={{ color: "#8892A4", fontSize: 11 }}>{timeAgo(q.created_at)}</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default QueryHistory;
