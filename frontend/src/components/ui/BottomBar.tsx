import { usePortfolioStore } from "@/store/portfolioStore";
import { formatCurrency } from "@/utils/formatters";

const BottomBar = () => {
  const { totalValue, buyingPower } = usePortfolioStore();

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-between"
      style={{
        height: 48,
        background: "rgba(15,24,32,0.95)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        borderTop: "1px solid #1E2D40",
        padding: "0 32px",
      }}
    >
      <div className="flex items-center gap-3">
        <span style={{ color: "#8892A4", fontSize: 11, letterSpacing: "0.1em" }}>Portfolio Value</span>
        <span className="font-mono" style={{ color: "#FFFFFF", fontSize: 14, fontWeight: 600 }}>
          {formatCurrency(totalValue)}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <span style={{ color: "#8892A4", fontSize: 11, letterSpacing: "0.1em" }}>Buying Power</span>
        <span className="font-mono" style={{ color: "#F0A500", fontSize: 14, fontWeight: 600 }}>
          {formatCurrency(buyingPower)}
        </span>
      </div>
    </div>
  );
};

export default BottomBar;
