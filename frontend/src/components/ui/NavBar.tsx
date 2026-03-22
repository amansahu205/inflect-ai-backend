import { useState, useRef, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { supabase } from "@/integrations/supabase/client";
import logo from "@/assets/inflect-logo.png";

const navLinks = [
  { to: "/app/research", label: "Research" },
  { to: "/app/portfolio", label: "Portfolio" },
];

const NavBar = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const initial = user?.email?.charAt(0).toUpperCase() || "?";

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate("/", { replace: true });
  };

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between"
      style={{
        height: 56,
        background: "rgba(8,12,20,0.95)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderBottom: "1px solid #1E2D40",
        padding: "0 32px",
      }}
    >
      <img
        src={logo}
        alt="Inflect"
        style={{ height: 32, cursor: "pointer" }}
        className="object-contain"
        onClick={() => navigate("/")}
      />

      <div className="flex items-center gap-6">
        {navLinks.map((link) => {
          const isActive = location.pathname === link.to;
          return (
            <Link
              key={link.to}
              to={link.to}
              className="transition-colors duration-200"
              style={{
                color: isActive ? "#F0A500" : "#8892A4",
                fontSize: 14,
                fontWeight: isActive ? 600 : 400,
                paddingBottom: 4,
                borderBottom: isActive ? "2px solid #F0A500" : "2px solid transparent",
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.color = "#8892A4";
              }}
            >
              {link.label}
            </Link>
          );
        })}

        <div className="relative" ref={ref}>
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center justify-center"
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: "rgba(240,165,0,0.2)",
              border: "1px solid #F0A500",
              color: "#F0A500",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            {initial}
          </button>

          {open && (
            <div
              className="absolute right-0 top-full mt-2"
              style={{
                background: "#0F1820",
                border: "1px solid #1E2D40",
                borderRadius: 8,
                padding: 4,
                minWidth: 140,
              }}
            >
              <button
                onClick={handleLogout}
                className="w-full text-left transition-colors duration-150"
                style={{ padding: "8px 16px", color: "#8892A4", fontSize: 14, borderRadius: 6 }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#1E2D40";
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "#8892A4";
                }}
              >
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

export default NavBar;
