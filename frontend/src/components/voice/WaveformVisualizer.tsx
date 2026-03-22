interface WaveformVisualizerProps {
  isActive: boolean;
  color?: string;
  barCount?: number;
}

const delays = [0, 80, 160, 0, 120, 60, 200];

const WaveformVisualizer = ({ isActive, color = "#F0A500", barCount = 7 }: WaveformVisualizerProps) => (
  <div className="flex items-center justify-center gap-1" style={{ height: 32 }}>
    {Array.from({ length: barCount }).map((_, i) => (
      <div
        key={i}
        style={{
          width: 4,
          borderRadius: 2,
          background: color,
          height: isActive ? undefined : 6,
          animation: isActive ? `barPulse 0.8s ease-in-out ${delays[i % delays.length]}ms infinite` : "none",
          transition: "height 0.2s ease",
        }}
        className={isActive ? "" : ""}
      />
    ))}
  </div>
);

export default WaveformVisualizer;
