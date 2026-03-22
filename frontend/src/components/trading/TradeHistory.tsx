import { formatCurrency, formatDate } from "@/utils/formatters";
import type { Trade } from "@/types/api";

interface TradeHistoryProps {
  trades: Trade[];
  isLoading: boolean;
}

const columns = ["DATE", "SIDE", "TICKER", "SHARES", "PRICE", "TOTAL"];

const TradeHistory = ({ trades, isLoading }: TradeHistoryProps) => {
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

  if (trades.length === 0) {
    return (
      <div style={{ background: "#0F1820", border: "1px solid #1E2D40", borderRadius: 12, padding: 40, textAlign: "center" }}>
        <p style={{ color: "#8892A4", fontSize: 14 }}>No trades yet.</p>
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
          {trades.map((t) => {
            const isBuy = t.side === "buy";
            return (
              <tr
                key={t.id}
                className="transition-colors duration-150"
                style={{ borderBottom: "1px solid rgba(30,45,64,0.5)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(240,165,0,0.03)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <td style={{ padding: "16px 20px", color: "#8892A4", fontSize: 13 }}>
                  {formatDate(t.created_at)}
                </td>
                <td className="font-mono" style={{ padding: "16px 20px", color: isBuy ? "#00D68F" : "#E05555", fontWeight: 700, fontSize: 13 }}>
                  {t.side.toUpperCase()}
                </td>
                <td className="font-mono" style={{ padding: "16px 20px", color: "#F0A500", fontWeight: 700, fontSize: 14 }}>
                  {t.ticker}
                </td>
                <td className="font-mono" style={{ padding: "16px 20px", color: "white", fontSize: 14 }}>
                  {t.quantity}
                </td>
                <td className="font-mono" style={{ padding: "16px 20px", color: "white", fontSize: 14 }}>
                  {formatCurrency(t.fill_price)}
                </td>
                <td className="font-mono" style={{ padding: "16px 20px", color: "white", fontWeight: 700, fontSize: 14 }}>
                  {formatCurrency(t.total_value)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default TradeHistory;
