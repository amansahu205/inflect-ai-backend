import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import Skeleton from "@/components/ui/InflectSkeleton";

interface LineChartProps {
  data: { x: string[]; y: number[] };
  title: string;
  yAxisLabel: string;
  ticker: string;
  filingDates?: string[];
}

const LineChart = ({ data, title, yAxisLabel, ticker, filingDates }: LineChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || data.x.length === 0) return;

    const shapes: Partial<Plotly.Shape>[] = (filingDates || []).map((d) => ({
      type: "line",
      x0: d,
      x1: d,
      y0: 0,
      y1: 1,
      yref: "paper",
      line: { color: "rgba(0,214,143,0.4)", width: 1, dash: "dot" },
    }));

    const annotations: Partial<Plotly.Annotations>[] = (filingDates || []).map((d) => ({
      x: d,
      y: 1,
      yref: "paper",
      text: "📎",
      showarrow: false,
      font: { size: 10 },
      yanchor: "bottom",
    }));

    const trace: Partial<Plotly.PlotData> = {
      x: data.x,
      y: data.y,
      type: "scatter",
      mode: "lines+markers",
      line: { color: "#F0A500", width: 2 },
      marker: { color: "#F0A500", size: 4 },
      fill: "tozeroy",
      fillcolor: "rgba(240,165,0,0.06)",
      hovertemplate: "%{x}<br>%{y:,.2f}<extra></extra>",
    };

    const layout: Partial<Plotly.Layout> = {
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { color: "#8892A4", size: 11 },
      xaxis: {
        gridcolor: "rgba(30,45,64,0.6)",
        tickcolor: "#8892A4",
        linecolor: "#1E2D40",
      },
      yaxis: {
        gridcolor: "rgba(30,45,64,0.6)",
        tickcolor: "#8892A4",
        linecolor: "#1E2D40",
        title: { text: yAxisLabel, font: { size: 11, color: "#8892A4" } },
      },
      margin: { l: 50, r: 20, t: 20, b: 40 },
      hovermode: "x unified",
      hoverlabel: {
        bgcolor: "#0F1820",
        bordercolor: "#1E2D40",
        font: { color: "white" },
      },
      shapes,
      annotations,
      autosize: true,
    };

    Plotly.newPlot(containerRef.current, [trace], layout, {
      displayModeBar: false,
      responsive: true,
    }).then(() => setReady(true));

    return () => {
      if (containerRef.current) Plotly.purge(containerRef.current);
    };
  }, [data, yAxisLabel, filingDates]);

  return (
    <div
      style={{
        background: "#0F1820",
        border: "1px solid #1E2D40",
        borderRadius: 12,
        padding: 16,
      }}
    >
      <p className="font-mono" style={{ color: "#F0A500", fontSize: 13, marginBottom: 12 }}>
        {ticker} · {title}
      </p>
      {!ready && (
        <div className="flex flex-col gap-2">
          <Skeleton width="100%" height={200} borderRadius={8} />
        </div>
      )}
      <div ref={containerRef} style={{ width: "100%", minHeight: 260, display: ready ? "block" : "none" }} />
    </div>
  );
};

export default LineChart;
