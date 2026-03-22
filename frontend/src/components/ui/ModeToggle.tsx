interface ModeToggleProps {
  activeMode: "voice" | "chat";
  onChange: (mode: "voice" | "chat") => void;
}

const ModeToggle = ({ activeMode, onChange }: ModeToggleProps) => {
  const btn = (mode: "voice" | "chat", emoji: string, label: string) => {
    const isActive = activeMode === mode;
    return (
      <button
        onClick={() => onChange(mode)}
        className="flex items-center gap-1.5 transition-all duration-150"
        style={{
          borderRadius: 20,
          padding: "6px 16px",
          fontSize: 13,
          fontWeight: isActive ? 700 : 400,
          background: isActive ? "#F0A500" : "transparent",
          color: isActive ? "#080C14" : "#8892A4",
          border: "none",
          cursor: "pointer",
        }}
        onMouseEnter={(e) => {
          if (!isActive) e.currentTarget.style.color = "#FFFFFF";
        }}
        onMouseLeave={(e) => {
          if (!isActive) e.currentTarget.style.color = "#8892A4";
        }}
      >
        {emoji} {label}
      </button>
    );
  };

  return (
    <div
      className="inline-flex"
      style={{
        background: "#0F1820",
        border: "1px solid #1E2D40",
        borderRadius: 24,
        padding: 4,
      }}
    >
      {btn("voice", "🎙️", "Voice")}
      {btn("chat", "💬", "Chat")}
    </div>
  );
};

export default ModeToggle;
