import { useNavigate } from "react-router-dom";
import { formatCurrency } from "@/utils/formatters";
import type { Position } from "@/types/api";

interface PositionsTableProps {
  positions: Position[];
  isLoading: boolean;
}

const columns = ["TICKER", "SHARES", "AVG COST", "CURRENT PRICE", "UNREAL. P&L", "CHANGE"];

const PositionsTable = ({ positions, isLoading }: PositionsTableProps) => {
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div style={{ background: "#0F1820", border: "1px solid #1E2D40", borderRadius: 12, padding: 40 }}>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              height: 20,
              background: "linear-gradient(90deg, #1E2D40 25%, #253548 50%, #1E2D40 75%)",
              backgroundSize: "200% 100%",
              animation: "shimmer 1.5s infinite",
              borderRadius: 4,
              marginBottom: i < 2 ? 12 : 0,
            }}
          />
        ))}
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div style={{ background: "#0F1820", border: "1px solid #1E2D40", borderRadius: 12, padding: 40, textAlign: "center" }}>
        <p style={{ color: "#8892A4", fontSize: 14, marginBottom: 16 }}>No positions yet.</p>
        <button
          onClick={() => navigate("/app/research")}
          className="transition-colors duration-150"
          style={{
            border: "1px solid rgba(240,165,0,0.4)",
            background: "transparent",
            borderRadius: 16,
            padding: "8px 18px",
            color: "#F0A500",
            fontSize: 13,
            cursor: "pointer",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(240,165,0,0.08)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          Go to Research →
        </button>
      </div>
    );
  }

  return (
    <div style={{ background: "#0F1820", border: "1px solid #1E2D40", borderRadius: 12, overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#080C14", borderBottom: "1px solid #1E2D40" }}>
            {columns.map((col) => (
              <th
                key={col}
                style={{
                  padding: "12px 20px",
                  textAlign: "left",
                  color: "#8892A4",
                  fontSize: 11,
                  letterSpacing: "0.1em",
                  fontWeight: 500,
                }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => {
            // Mock current price — replace with real data
            const currentPrice = p.avg_cost_basis * (1 + (Math.random() - 0.45) * 0.1);
            const unrealPnl = (currentPrice - p.avg_cost_basis) * p.quantity;
            const changePct = ((currentPrice - p.avg_cost_basis) / p.avg_cost_basis) * 100;
            const isUp = unrealPnl >= 0;
            const color = isUp ? "#00D68F" : "#E05555";

            return (
              <tr
                key={p.id}
                className="transition-colors duration-150"
                style={{ borderBottom: "1px solid rgba(30,45,64,0.5)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(240,165,0,0.03)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <td className="font-mono" style={{ padding: "16px 20px", color: "#F0A500", fontWeight: 700, fontSize: 14 }}>
                  {p.ticker}
                </td>
                <td className="font-mono" style={{ padding: "16px 20px", color: "white", fontSize: 14 }}>
                  {p.quantity}
                </td>
                <td className="font-mono" style={{ padding: "16px 20px", color: "white", fontSize: 14 }}>
                  {formatCurrency(p.avg_cost_basis)}
                </td>
                <td className="font-mono" style={{ padding: "16px 20px", color: "white", fontSize: 14 }}>
                  {formatCurrency(currentPrice)}
                </td>
                <td className="font-mono" style={{ padding: "16px 20px", color, fontSize: 14 }}>
                  {isUp ? "+" : ""}{formatCurrency(unrealPnl)}
                </td>
                <td style={{ padding: "16px 20px" }}>
                  <span
                    className="font-mono"
                    style={{
                      background: isUp ? "rgba(0,214,143,0.15)" : "rgba(224,85,85,0.15)",
                      color,
                      borderRadius: 12,
                      padding: "4px 10px",
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    {isUp ? "▲" : "▼"} {isUp ? "+" : ""}{changePct.toFixed(2)}%
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default PositionsTable;
