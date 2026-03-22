import { useEffect } from "react";
import type { TradeOrder } from "@/types/api";
import { formatCurrency } from "@/utils/formatters";
import { usePortfolioStore } from "@/store/portfolioStore";

interface TradeModalProps {
  order: TradeOrder | null;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
  fillResult: { fill_price: number } | null;
}

const TradeModal = ({ order, onConfirm, onCancel, isLoading, fillResult }: TradeModalProps) => {
  // Auto-close after fill
  useEffect(() => {
    if (fillResult) {
      const t = setTimeout(onConfirm, 3000);
      return () => clearTimeout(t);
    }
  }, [fillResult, onConfirm]);

  if (!order) return null;

  const isBuy = order.side === "buy";
  const { buyingPower } = usePortfolioStore.getState();
  const isLargeOrder = order.estimated_total > buyingPower * 0.2;

  return (
    <div
      className="fixed inset-0 flex items-center justify-center"
      style={{ background: "rgba(8,12,20,0.85)", backdropFilter: "blur(4px)", zIndex: 200 }}
    >
      <div
        style={{
          background: "#0F1820",
          border: "1px solid #F0A500",
          borderRadius: 16,
          padding: 32,
          width: 480,
          maxWidth: "calc(100vw - 48px)",
          animation: "tradeModalIn 250ms ease-out",
        }}
      >
        {/* SUCCESS STATE */}
        {fillResult ? (
          <div className="flex flex-col items-center" style={{ padding: "16px 0" }}>
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <circle
                cx="32" cy="32" r="28"
                stroke="#00D68F" strokeWidth="3"
                fill="none"
                style={{
                  strokeDasharray: 176,
                  strokeDashoffset: 0,
                  animation: "checkCircle 500ms ease-out",
                }}
              />
              <polyline
                points="20,34 28,42 44,24"
                stroke="#00D68F" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"
                fill="none"
                style={{
                  strokeDasharray: 40,
                  strokeDashoffset: 0,
                  animation: "checkMark 400ms ease-out 200ms both",
                }}
              />
            </svg>
            <p style={{ color: "#00D68F", fontSize: 18, fontWeight: 700, marginTop: 16 }}>Order Filled!</p>
            <p style={{ color: "white", fontSize: 14, marginTop: 8 }}>
              {order.quantity} {order.ticker} at {formatCurrency(fillResult.fill_price)}
            </p>
          </div>
        ) : isLoading ? (
          /* LOADING STATE */
          <div className="flex flex-col items-center" style={{ padding: "24px 0" }}>
            <div
              style={{
                width: 32,
                height: 32,
                border: "3px solid rgba(240,165,0,0.3)",
                borderTopColor: "#F0A500",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }}
            />
            <p style={{ color: "#8892A4", fontSize: 14, textAlign: "center", marginTop: 12 }}>
              Executing order...
            </p>
          </div>
        ) : (
          /* CONFIRM STATE */
          <>
            <h2 style={{ color: "white", fontSize: 18, fontWeight: 700, marginBottom: 24 }}>Confirm Order</h2>

            <div style={{ background: "#080C14", borderRadius: 8, padding: 16, marginBottom: 24 }}>
              {[
                { label: "Action", value: isBuy ? "BUY" : "SELL", color: isBuy ? "#00D68F" : "#E05555", bold: true },
                { label: "Ticker", value: order.ticker, color: "#F0A500", mono: true },
                { label: "Shares", value: String(order.quantity), color: "white", mono: true },
                { label: "Order Type", value: "Market", color: "#8892A4" },
                { label: "Est. Price", value: formatCurrency(order.estimated_price), color: "white", mono: true },
                { label: "Est. Total", value: formatCurrency(order.estimated_total), color: "white", mono: true, bold: true },
                { label: "Slippage", value: "±0.05%", color: "#8892A4", small: true },
              ].map((row, i, arr) => (
                <div
                  key={row.label}
                  className="flex justify-between"
                  style={{
                    padding: "8px 0",
                    borderBottom: i < arr.length - 1 ? "1px solid #1E2D40" : "none",
                  }}
                >
                  <span style={{ color: "#8892A4", fontSize: row.small ? 12 : 13 }}>{row.label}:</span>
                  <span
                    className={row.mono ? "font-mono" : ""}
                    style={{
                      color: row.color,
                      fontSize: row.small ? 12 : 13,
                      fontWeight: row.bold ? 700 : 400,
                    }}
                  >
                    {row.value}
                  </span>
                </div>
              ))}
            </div>

            {isLargeOrder && (
              <div
                style={{
                  background: "rgba(240,165,0,0.08)",
                  border: "1px solid rgba(240,165,0,0.2)",
                  borderRadius: 6,
                  padding: "8px 12px",
                  marginBottom: 16,
                  color: "#F0A500",
                  fontSize: 12,
                }}
              >
                ⚠️ This is a large position
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={onCancel}
                className="flex-1 transition-colors duration-150"
                style={{
                  background: "transparent",
                  border: "1px solid #1E2D40",
                  borderRadius: 8,
                  padding: 12,
                  color: "#8892A4",
                  cursor: "pointer",
                  fontSize: 14,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#8892A4"; e.currentTarget.style.color = "white"; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#1E2D40"; e.currentTarget.style.color = "#8892A4"; }}
              >
                Cancel
              </button>
              <button
                onClick={onConfirm}
                className="flex-1 transition-colors duration-150"
                style={{
                  background: "#F0A500",
                  border: "none",
                  borderRadius: 8,
                  padding: 12,
                  color: "#080C14",
                  fontWeight: 700,
                  cursor: "pointer",
                  fontSize: 14,
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#D4920A")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "#F0A500")}
              >
                Confirm
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default TradeModal;
