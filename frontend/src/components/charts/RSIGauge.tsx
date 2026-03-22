import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";

interface RSIGaugeProps {
  value: number;
  ticker: string;
}

const getLabel = (v: number) => {
  if (v < 30) return { text: "Oversold", color: "#00D68F" };
  if (v > 70) return { text: "Overbought", color: "#E05555" };
  return { text: "Neutral", color: "#8892A4" };
};

const RSIGauge = ({ value, ticker }: RSIGaugeProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const label = getLabel(value);

  useEffect(() => {
    if (!ref.current) return;

    const trace: Partial<Plotly.PlotData> & { gauge: any } = {
      type: "indicator" as any,
      mode: "gauge+number" as any,
      value,
      number: { font: { color: "#F0A500", size: 28 } },
      gauge: {
        axis: { range: [0, 100], tickcolor: "#8892A4", dtick: 20 },
        bar: { color: "#F0A500" },
        bgcolor: "transparent",
        bordercolor: "#1E2D40",
        steps: [
          { range: [0, 30], color: "rgba(224,85,85,0.2)" },
          { range: [30, 70], color: "rgba(136,146,164,0.1)" },
          { range: [70, 100], color: "rgba(0,214,143,0.2)" },
        ],
        threshold: {
          line: { color: "white", width: 2 },
          value,
        },
        shape: "angular",
      },
    };

    const layout: Partial<Plotly.Layout> = {
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { color: "#8892A4", size: 11 },
      margin: { l: 30, r: 30, t: 30, b: 0 },
      height: 180,
      autosize: true,
    };

    Plotly.newPlot(ref.current, [trace as any], layout, {
      displayModeBar: false,
      responsive: true,
    }).then(() => setReady(true));

    return () => {
      if (ref.current) Plotly.purge(ref.current);
    };
  }, [value]);

  return (
    <div
      style={{
        background: "#0F1820",
        border: "1px solid #1E2D40",
        borderRadius: 12,
        padding: 16,
        textAlign: "center",
      }}
    >
      <p className="font-mono" style={{ color: "#F0A500", fontSize: 13, marginBottom: 4 }}>
        {ticker} · RSI
      </p>
      <div ref={ref} style={{ width: "100%", display: ready ? "block" : "none" }} />
      <p className="font-mono" style={{ color: label.color, fontSize: 13, fontWeight: 700, marginTop: 4 }}>
        {label.text}
      </p>
    </div>
  );
};

export default RSIGauge;
